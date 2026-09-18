"""Pydantic response models for the AMRAS API.

Kept separate from core/models.py on purpose: these are the API's public
contract (what a client sees over the wire), while core/models.py is the
engine's internal domain representation. Converting explicitly between the
two means a change to one never silently changes the other.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HealthOut(BaseModel):
    status: str
    engine_running: bool


class SystemStatusOut(BaseModel):
    algorithms_online: bool
    data_feed_online: bool
    broker_connected: bool
    risk_engine_active: bool
    kill_switch_halted: bool
    last_cycle_at: datetime | None
    last_error: str | None


class PortfolioOut(BaseModel):
    equity: float


class RegimeOut(BaseModel):
    symbol: str
    regime: str


class PositionOut(BaseModel):
    symbol: str
    side: str
    entry_price: float
    amount: float
    stop_loss: float
    take_profit: float
    strategy_name: str
    opened_at: datetime
    breakeven_applied: bool
    trailing_active: bool
    last_price: float | None = None
    unrealized_pnl: float | None = None


class SignalOut(BaseModel):
    symbol: str
    action: str
    strategy_name: str
    regime: str
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    risk_reward_ratio: float
    generated_at: datetime


class OrderOut(BaseModel):
    order_id: str
    symbol: str
    side: str
    order_type: str
    status: str
    requested_price: float | None
    filled_price: float | None
    amount: float
    filled_amount: float
    fee: float
    fee_currency: str
    slippage: float | None
    latency_ms: float
    timestamp: datetime
