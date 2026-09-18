"""Multilevel Risk Engine: position sizing, R:R validation, active trade
management (break-even / ATR trailing stop) and the daily kill switch.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from core.enums import PositionSide
from core.models import Position, Signal

logger = logging.getLogger("amras.risk")


@dataclass(slots=True)
class RiskConfig:
    risk_per_trade_pct: float = 0.75  # % of equity risked per trade
    min_risk_reward: float = 1.5
    atr_period: int = 14
    atr_sl_multiplier: float = 1.5
    atr_trailing_multiplier: float = 2.0
    breakeven_trigger_rr: float = 1.0  # move SL to entry once price reaches 1R
    max_daily_drawdown_pct: float = 3.0
    kill_switch_cooldown_hours: int = 24


@dataclass(slots=True)
class _DailyState:
    day: date
    starting_equity: float
    peak_equity: float


class KillSwitchActive(Exception):
    """Raised when trading is halted by the daily kill switch."""


class RiskManager:
    def __init__(self, config: RiskConfig | None = None) -> None:
        self.config = config or RiskConfig()
        self._daily_state: _DailyState | None = None
        self._kill_switch_until: datetime | None = None

    # ---- position sizing ---------------------------------------------------
    def calculate_position_size(self, equity: float, entry_price: float, stop_loss: float) -> float:
        risk_amount = equity * (self.config.risk_per_trade_pct / 100)
        stop_distance = abs(entry_price - stop_loss)
        if stop_distance <= 0:
            raise ValueError("Stop distance must be positive to size a position")
        size = risk_amount / stop_distance
        logger.debug(
            "Sized position: equity=%.2f risk_amount=%.2f stop_distance=%.6f -> size=%.6f",
            equity, risk_amount, stop_distance, size,
        )
        return size

    def stop_loss_from_atr(self, entry_price: float, atr_value: float, side: PositionSide) -> float:
        offset = atr_value * self.config.atr_sl_multiplier
        return entry_price - offset if side == PositionSide.LONG else entry_price + offset

    # ---- signal validation ---------------------------------------------------
    def validate_signal(self, signal: Signal) -> bool:
        if signal.risk_reward_ratio < self.config.min_risk_reward:
            logger.info(
                "Signal rejected for %s: R:R %.2f below minimum %.2f",
                signal.symbol, signal.risk_reward_ratio, self.config.min_risk_reward,
            )
            return False
        return True

    # ---- active trade management ---------------------------------------------------
    def apply_breakeven(self, position: Position, current_price: float) -> bool:
        if position.breakeven_applied:
            return False
        direction = 1 if position.side == PositionSide.LONG else -1
        r_distance = abs(position.entry_price - position.stop_loss)
        if r_distance <= 0:
            return False
        progress_r = ((current_price - position.entry_price) * direction) / r_distance
        if progress_r >= self.config.breakeven_trigger_rr:
            position.stop_loss = position.entry_price
            position.breakeven_applied = True
            logger.info("Breakeven applied to %s position on %s", position.side, position.symbol)
            return True
        return False

    def apply_trailing_stop(self, position: Position, current_price: float, atr_value: float) -> bool:
        offset = atr_value * self.config.atr_trailing_multiplier
        if position.side == PositionSide.LONG:
            new_stop = current_price - offset
            if new_stop > position.stop_loss:
                position.stop_loss = new_stop
                position.trailing_active = True
                logger.info("Trailing stop updated for %s: new SL=%.6f", position.symbol, new_stop)
                return True
        else:
            new_stop = current_price + offset
            if new_stop < position.stop_loss:
                position.stop_loss = new_stop
                position.trailing_active = True
                logger.info("Trailing stop updated for %s: new SL=%.6f", position.symbol, new_stop)
                return True
        return False

    # ---- daily kill switch ---------------------------------------------------
    def start_of_day(self, equity: float) -> None:
        today = datetime.now(timezone.utc).date()
        if self._daily_state is None or self._daily_state.day != today:
            self._daily_state = _DailyState(day=today, starting_equity=equity, peak_equity=equity)
            logger.info("New trading day initialized. Starting equity=%.2f", equity)

    def register_equity(self, equity: float) -> None:
        if self._daily_state is None:
            self.start_of_day(equity)
            return

        today = datetime.now(timezone.utc).date()
        if self._daily_state.day != today:
            self.start_of_day(equity)
            return

        self._daily_state.peak_equity = max(self._daily_state.peak_equity, equity)
        drawdown_pct = ((self._daily_state.starting_equity - equity) / self._daily_state.starting_equity) * 100
        if drawdown_pct >= self.config.max_daily_drawdown_pct and self._kill_switch_until is None:
            self._trigger_kill_switch(drawdown_pct)

    def _trigger_kill_switch(self, drawdown_pct: float) -> None:
        self._kill_switch_until = datetime.now(timezone.utc) + timedelta(
            hours=self.config.kill_switch_cooldown_hours
        )
        logger.critical(
            "KILL SWITCH TRIGGERED: daily drawdown %.2f%% >= limit %.2f%%. Trading halted until %s",
            drawdown_pct, self.config.max_daily_drawdown_pct, self._kill_switch_until.isoformat(),
        )

    @property
    def is_trading_allowed(self) -> bool:
        if self._kill_switch_until is None:
            return True
        if datetime.now(timezone.utc) >= self._kill_switch_until:
            logger.info("Kill switch cooldown expired. Trading resumed.")
            self._kill_switch_until = None
            return True
        return False

    def ensure_trading_allowed(self) -> None:
        if not self.is_trading_allowed:
            raise KillSwitchActive(f"Trading halted until {self._kill_switch_until.isoformat()}")
