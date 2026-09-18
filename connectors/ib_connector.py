"""Placeholder adapter for Interactive Brokers (via `ib_insync` / `ib_async`).

Implement each method against the IB Gateway/TWS API once account access is
available. Kept structurally identical to CCXTConnector so AMRAS core code
requires zero changes to trade through it once implemented.
"""
from __future__ import annotations

from connectors.base_connector import Balance, BaseExchangeConnector, Ticker
from core.models import Candle, OrderRequest, OrderResult


class IBConnector(BaseExchangeConnector):
    def get_balance(self, currency: str = "USD") -> Balance:
        raise NotImplementedError("IBConnector.get_balance is not implemented yet")

    def get_ticker(self, symbol: str) -> Ticker:
        raise NotImplementedError("IBConnector.get_ticker is not implemented yet")

    def create_order(self, request: OrderRequest) -> OrderResult:
        raise NotImplementedError("IBConnector.create_order is not implemented yet")

    def cancel_order(self, symbol: str, order_id: str) -> bool:
        raise NotImplementedError("IBConnector.cancel_order is not implemented yet")

    def get_historical_klines(self, symbol: str, timeframe: str, limit: int = 500) -> list[Candle]:
        raise NotImplementedError("IBConnector.get_historical_klines is not implemented yet")
