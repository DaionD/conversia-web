"""CCXT-backed connector: compatible with Binance, Bybit, KuCoin, OKX, Kraken
and 100+ other exchanges supported by the ccxt library, through a single
implementation of BaseExchangeConnector.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import ccxt
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from connectors.base_connector import Balance, BaseExchangeConnector, Ticker
from connectors.exceptions import AuthenticationError, InsufficientFundsError, NetworkError, OrderExecutionError
from core.enums import OrderStatus, OrderType
from core.models import Candle, OrderRequest, OrderResult

logger = logging.getLogger("amras.connector.ccxt")

_RETRYABLE = (ccxt.NetworkError, ccxt.RequestTimeout, ccxt.ExchangeNotAvailable)

_ORDER_TYPE_MAP = {
    OrderType.MARKET: "market",
    OrderType.LIMIT: "limit",
    OrderType.STOP_MARKET: "stop_market",
    OrderType.STOP_LIMIT: "stop_limit",
}

_STATUS_MAP = {
    "closed": OrderStatus.FILLED,
    "open": OrderStatus.OPEN,
    "canceled": OrderStatus.CANCELED,
    "expired": OrderStatus.EXPIRED,
    "rejected": OrderStatus.REJECTED,
}


def _retry_policy():
    """Automatic reconnection policy for transient network failures."""
    return retry(
        retry=retry_if_exception_type(_RETRYABLE),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )


class CCXTConnector(BaseExchangeConnector):
    def __init__(
        self,
        exchange_id: str,
        api_key: str,
        api_secret: str,
        password: str = "",
        sandbox: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(api_key, api_secret, **kwargs)
        if not hasattr(ccxt, exchange_id):
            raise ValueError(f"CCXT does not support exchange id '{exchange_id}'")

        exchange_class = getattr(ccxt, exchange_id)
        config = {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": kwargs.pop("options", {}),
        }
        if password:
            config["password"] = password
        config.update(kwargs)

        self.exchange: ccxt.Exchange = exchange_class(config)
        if sandbox:
            self.exchange.set_sandbox_mode(True)
        self.exchange_id = exchange_id
        logger.info("CCXT connector initialized for %s (sandbox=%s)", exchange_id, sandbox)

    @_retry_policy()
    def get_balance(self, currency: str = "USDT") -> Balance:
        try:
            raw = self.exchange.fetch_balance()
        except ccxt.AuthenticationError as exc:
            raise AuthenticationError(str(exc)) from exc
        except _RETRYABLE as exc:
            raise NetworkError(str(exc)) from exc

        total = raw.get("total", {}).get(currency, 0.0) or 0.0
        free = raw.get("free", {}).get(currency, 0.0) or 0.0
        used = raw.get("used", {}).get(currency, 0.0) or 0.0
        return Balance(total=total, free=free, used=used, currency=currency)

    @_retry_policy()
    def get_ticker(self, symbol: str) -> Ticker:
        try:
            raw = self.exchange.fetch_ticker(symbol)
        except _RETRYABLE as exc:
            raise NetworkError(str(exc)) from exc

        return Ticker(
            symbol=symbol,
            bid=raw.get("bid") or 0.0,
            ask=raw.get("ask") or 0.0,
            last=raw.get("last") or 0.0,
            timestamp=datetime.fromtimestamp((raw.get("timestamp") or 0) / 1000, tz=timezone.utc),
        )

    @_retry_policy()
    def create_order(self, request: OrderRequest) -> OrderResult:
        ccxt_type = _ORDER_TYPE_MAP[request.order_type]
        params = dict(request.params)
        if request.stop_price is not None:
            params["stopPrice"] = request.stop_price

        try:
            raw = self.exchange.create_order(
                symbol=request.symbol,
                type=ccxt_type,
                side=request.side.value,
                amount=request.amount,
                price=request.price,
                params=params,
            )
        except ccxt.InsufficientFunds as exc:
            raise InsufficientFundsError(str(exc)) from exc
        except _RETRYABLE as exc:
            raise NetworkError(str(exc)) from exc
        except ccxt.BaseError as exc:
            raise OrderExecutionError(str(exc)) from exc

        status = _STATUS_MAP.get(raw.get("status"), OrderStatus.PENDING)
        filled_amount = raw.get("filled") or 0.0
        if 0 < filled_amount < (raw.get("amount") or request.amount):
            status = OrderStatus.PARTIALLY_FILLED

        fee_info = raw.get("fee") or {}

        return OrderResult(
            order_id=str(raw.get("id")),
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            status=status,
            requested_price=request.price,
            filled_price=raw.get("average") or raw.get("price"),
            amount=request.amount,
            filled_amount=filled_amount,
            fee=fee_info.get("cost", 0.0) or 0.0,
            fee_currency=fee_info.get("currency", ""),
            raw=raw,
        )

    @_retry_policy()
    def cancel_order(self, symbol: str, order_id: str) -> bool:
        try:
            self.exchange.cancel_order(order_id, symbol)
            return True
        except ccxt.OrderNotFound:
            logger.warning("Order %s not found on %s during cancel", order_id, symbol)
            return False
        except _RETRYABLE as exc:
            raise NetworkError(str(exc)) from exc
        except ccxt.BaseError as exc:
            raise OrderExecutionError(str(exc)) from exc

    @_retry_policy()
    def get_historical_klines(self, symbol: str, timeframe: str, limit: int = 500) -> list[Candle]:
        try:
            raw = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        except _RETRYABLE as exc:
            raise NetworkError(str(exc)) from exc

        return [
            Candle(
                timestamp=datetime.fromtimestamp(ts / 1000, tz=timezone.utc),
                open=o, high=h, low=l, close=c, volume=v,
            )
            for ts, o, h, l, c, v in raw
        ]

    def close(self) -> None:
        if hasattr(self.exchange, "close"):
            self.exchange.close()
