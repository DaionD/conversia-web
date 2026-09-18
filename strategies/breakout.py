"""Breakout engine: pending stop orders at Donchian-channel support/resistance
levels, anticipating a volatility expansion. Active only while the Regime
Engine reports MarketRegime.VOLATILITY_COMPRESSION.

The generated Signal's `entry_price` is the pending trigger level (not the
current market price) -- the engine submits it as a STOP order rather than
a market order for signals produced in this regime.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

from core import indicators
from core.enums import MarketRegime, SignalAction
from core.models import Signal
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger("amras.strategy.breakout")


@dataclass(slots=True)
class BreakoutConfig:
    lookback_period: int = 20
    atr_period: int = 14
    trigger_buffer_atr: float = 0.1  # place the stop slightly beyond the level
    atr_sl_multiplier: float = 1.0
    reward_multiplier: float = 2.0


class BreakoutStrategy(BaseStrategy):
    regime = MarketRegime.VOLATILITY_COMPRESSION
    name = "breakout_pending_orders"

    def __init__(self, config: BreakoutConfig | None = None) -> None:
        self.config = config or BreakoutConfig()

    def generate_signal(self, ohlcv: pd.DataFrame) -> Signal | None:
        cfg = self.config
        if len(ohlcv) < cfg.lookback_period + 2:
            return None

        resistance = ohlcv["high"].rolling(cfg.lookback_period).max().iloc[-2]
        support = ohlcv["low"].rolling(cfg.lookback_period).min().iloc[-2]
        atr_value = float(indicators.atr(ohlcv, cfg.atr_period).iloc[-1])
        price = float(ohlcv["close"].iloc[-1])

        if pd.isna(resistance) or pd.isna(support) or pd.isna(atr_value) or atr_value <= 0:
            return None

        buffer = atr_value * cfg.trigger_buffer_atr
        distance_to_resistance = resistance - price
        distance_to_support = price - support

        if distance_to_resistance <= distance_to_support:
            trigger_price = resistance + buffer
            stop_loss = trigger_price - atr_value * cfg.atr_sl_multiplier
            take_profit = trigger_price + atr_value * cfg.atr_sl_multiplier * cfg.reward_multiplier
            action = SignalAction.BUY
        else:
            trigger_price = support - buffer
            stop_loss = trigger_price + atr_value * cfg.atr_sl_multiplier
            take_profit = trigger_price - atr_value * cfg.atr_sl_multiplier * cfg.reward_multiplier
            action = SignalAction.SELL

        return Signal(
            symbol=ohlcv.attrs.get("symbol", "UNKNOWN"),
            action=action,
            strategy_name=self.name,
            regime=self.regime,
            entry_price=trigger_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=0.6,
            metadata={"resistance": float(resistance), "support": float(support), "pending": True},
        )
