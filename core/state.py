"""Thread-safe in-memory snapshot of engine state.

AmrasEngine publishes into this store as it runs; the API layer reads from
it. This decouples the trading loop (which blocks on synchronous exchange
I/O) from HTTP/WebSocket request handling -- API reads never make a network
call to the exchange, they only read the latest published snapshot.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any

from core.enums import MarketRegime
from core.models import OrderResult, Position, Signal


@dataclass(slots=True)
class SystemStatus:
    algorithms_online: bool = False
    data_feed_online: bool = False
    broker_connected: bool = False
    risk_engine_active: bool = True
    kill_switch_halted: bool = False
    last_cycle_at: datetime | None = None
    last_error: str | None = None


@dataclass(slots=True)
class StateSnapshot:
    equity: float
    regimes: dict[str, MarketRegime]
    positions: dict[str, Position]
    last_prices: dict[str, float]
    recent_signals: list[Signal]
    recent_orders: list[OrderResult]
    status: SystemStatus


class EngineState:
    """Written by AmrasEngine, read by the API. All access is lock-guarded."""

    def __init__(self, max_history: int = 50) -> None:
        self._lock = threading.Lock()
        self._max_history = max_history
        self._equity: float = 0.0
        self._regimes: dict[str, MarketRegime] = {}
        self._positions: dict[str, Position] = {}
        self._last_prices: dict[str, float] = {}
        self._recent_signals: list[Signal] = []
        self._recent_orders: list[OrderResult] = []
        self._status = SystemStatus()

    # ---- writers (called by AmrasEngine) -------------------------------------------------
    def set_equity(self, equity: float) -> None:
        with self._lock:
            self._equity = equity

    def set_regime(self, symbol: str, regime: MarketRegime) -> None:
        with self._lock:
            self._regimes[symbol] = regime

    def set_price(self, symbol: str, price: float) -> None:
        with self._lock:
            self._last_prices[symbol] = price

    def upsert_position(self, position: Position) -> None:
        with self._lock:
            self._positions[position.symbol] = position

    def remove_position(self, symbol: str) -> None:
        with self._lock:
            self._positions.pop(symbol, None)

    def record_signal(self, signal: Signal) -> None:
        with self._lock:
            self._recent_signals.append(signal)
            del self._recent_signals[: -self._max_history]

    def record_order(self, order: OrderResult) -> None:
        with self._lock:
            self._recent_orders.append(order)
            del self._recent_orders[: -self._max_history]

    def update_status(self, **fields: Any) -> None:
        with self._lock:
            for key, value in fields.items():
                setattr(self._status, key, value)
            self._status.last_cycle_at = datetime.now(timezone.utc)

    def record_error(self, message: str) -> None:
        with self._lock:
            self._status.last_error = message

    # ---- reader (called by the API) -------------------------------------------------
    def snapshot(self) -> StateSnapshot:
        with self._lock:
            return StateSnapshot(
                equity=self._equity,
                regimes=dict(self._regimes),
                positions=dict(self._positions),
                last_prices=dict(self._last_prices),
                recent_signals=list(self._recent_signals),
                recent_orders=list(self._recent_orders),
                status=replace(self._status),
            )
