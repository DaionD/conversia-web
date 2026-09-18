"""Universal exchange/broker adapter contract.

Every connector (CCXT-backed, MT5, Interactive Brokers, ...) implements this
abstract base class. AMRAS core code only ever talks to `BaseExchangeConnector`,
never to a specific vendor SDK -- that is what makes the platform broker-agnostic.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from core.models import Candle, OrderRequest, OrderResult


@dataclass(slots=True)
class Balance:
    total: float
    free: float
    used: float
    currency: str = "USDT"


@dataclass(slots=True)
class Ticker:
    symbol: str
    bid: float
    ask: float
    last: float
    timestamp: datetime


class BaseExchangeConnector(ABC):
    """Abstract base every exchange/broker adapter must implement."""

    def __init__(self, api_key: str, api_secret: str, **kwargs) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.extra_params = kwargs

    @abstractmethod
    def get_balance(self, currency: str = "USDT") -> Balance:
        """Return total/free/used balance for the given quote currency."""

    @abstractmethod
    def get_ticker(self, symbol: str) -> Ticker:
        """Return the current bid/ask/last price for a symbol."""

    @abstractmethod
    def create_order(self, request: OrderRequest) -> OrderResult:
        """Submit an order (market, limit or stop) and return its execution result."""

    @abstractmethod
    def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel a pending order. Returns True if canceled, False if not found."""

    @abstractmethod
    def get_historical_klines(self, symbol: str, timeframe: str, limit: int = 500) -> list[Candle]:
        """Return the last `limit` OHLCV candles for a symbol/timeframe."""

    def close(self) -> None:
        """Optional hook for connectors holding persistent connections/sessions."""
        return None
