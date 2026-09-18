"""Plain data structures shared across the AMRAS core, strategies and connectors."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.enums import MarketRegime, OrderSide, OrderStatus, OrderType, PositionSide, SignalAction


@dataclass(slots=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(slots=True)
class Signal:
    symbol: str
    action: SignalAction
    strategy_name: str
    regime: MarketRegime
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def risk_reward_ratio(self) -> float:
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.entry_price)
        return reward / risk if risk else 0.0


@dataclass(slots=True)
class OrderRequest:
    symbol: str
    side: OrderSide
    order_type: OrderType
    amount: float
    price: float | None = None
    stop_price: float | None = None
    client_order_id: str | None = None
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OrderResult:
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    requested_price: float | None
    filled_price: float | None
    amount: float
    filled_amount: float
    fee: float = 0.0
    fee_currency: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    latency_ms: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def slippage(self) -> float | None:
        if self.requested_price is None or self.filled_price is None:
            return None
        return self.filled_price - self.requested_price


@dataclass(slots=True)
class Position:
    symbol: str
    side: PositionSide
    entry_price: float
    amount: float
    stop_loss: float
    take_profit: float
    strategy_name: str
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    breakeven_applied: bool = False
    trailing_active: bool = False
    initial_risk: float = 0.0

    def unrealized_pnl(self, current_price: float) -> float:
        direction = 1 if self.side == PositionSide.LONG else -1
        return (current_price - self.entry_price) * self.amount * direction
