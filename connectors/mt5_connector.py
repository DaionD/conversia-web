"""Placeholder adapter for MetaTrader 5 (via the `MetaTrader5` package).

Implement each method against the MT5 terminal API once broker credentials
and a running terminal are available. The class is kept structurally
identical to CCXTConnector so AMRAS core code requires zero changes to
trade through it once implemented.
"""
from __future__ import annotations

from connectors.base_connector import Balance, BaseExchangeConnector, Ticker
from core.models import Candle, OrderRequest, OrderResult


class MT5Connector(BaseExchangeConnector):
    def get_balance(self, currency: str = "USD") -> Balance:
        raise NotImplementedError("MT5Connector.get_balance is not implemented yet")

    def get_ticker(self, symbol: str) -> Ticker:
        raise NotImplementedError("MT5Connector.get_ticker is not implemented yet")

    def create_order(self, request: OrderRequest) -> OrderResult:
        raise NotImplementedError("MT5Connector.create_order is not implemented yet")

    def cancel_order(self, symbol: str, order_id: str) -> bool:
        raise NotImplementedError("MT5Connector.cancel_order is not implemented yet")

    def get_historical_klines(self, symbol: str, timeframe: str, limit: int = 500) -> list[Candle]:
        raise NotImplementedError("MT5Connector.get_historical_klines is not implemented yet")
