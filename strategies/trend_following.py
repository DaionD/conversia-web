"""Trend-Following engine: MA crossover with an ADX strength filter.
Active only while the Regime Engine reports MarketRegime.TREND.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

from core import indicators
from core.enums import MarketRegime, SignalAction
from core.models import Signal
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger("amras.strategy.trend")


@dataclass(slots=True)
class TrendFollowingConfig:
    fast_ma_period: int = 50
    slow_ma_period: int = 200
    adx_period: int = 14
    adx_min_strength: float = 20.0
    atr_period: int = 14
    atr_sl_multiplier: float = 1.5
    reward_multiplier: float = 2.5  # combined with atr_sl_multiplier gives the R:R


class TrendFollowingStrategy(BaseStrategy):
    regime = MarketRegime.TREND
    name = "trend_following_ma_crossover"

    def __init__(self, config: TrendFollowingConfig | None = None) -> None:
        self.config = config or TrendFollowingConfig()

    def generate_signal(self, ohlcv: pd.DataFrame) -> Signal | None:
        cfg = self.config
        if len(ohlcv) < cfg.slow_ma_period + 2:
            return None

        fast = indicators.sma(ohlcv["close"], cfg.fast_ma_period)
        slow = indicators.sma(ohlcv["close"], cfg.slow_ma_period)
        adx = indicators.adx(ohlcv, cfg.adx_period)
        atr = indicators.atr(ohlcv, cfg.atr_period)

        if fast.iloc[-2:].isna().any() or slow.iloc[-2:].isna().any() or pd.isna(adx.iloc[-1]):
            return None

        crossed_up = fast.iloc[-2] <= slow.iloc[-2] and fast.iloc[-1] > slow.iloc[-1]
        crossed_down = fast.iloc[-2] >= slow.iloc[-2] and fast.iloc[-1] < slow.iloc[-1]
        strong_trend = adx.iloc[-1] >= cfg.adx_min_strength

        if not strong_trend or (not crossed_up and not crossed_down):
            return None

        price = float(ohlcv["close"].iloc[-1])
        atr_value = float(atr.iloc[-1])
        if pd.isna(atr_value) or atr_value <= 0:
            return None

        confidence = min(adx.iloc[-1] / 50, 1.0)

        if crossed_up:
            stop_loss = price - atr_value * cfg.atr_sl_multiplier
            take_profit = price + atr_value * cfg.atr_sl_multiplier * cfg.reward_multiplier
            action = SignalAction.BUY
        else:
            stop_loss = price + atr_value * cfg.atr_sl_multiplier
            take_profit = price - atr_value * cfg.atr_sl_multiplier * cfg.reward_multiplier
            action = SignalAction.SELL

        return Signal(
            symbol=ohlcv.attrs.get("symbol", "UNKNOWN"),
            action=action,
            strategy_name=self.name,
            regime=self.regime,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confidence=confidence,
            metadata={
                "adx": float(adx.iloc[-1]),
                "fast_ma": float(fast.iloc[-1]),
                "slow_ma": float(slow.iloc[-1]),
            },
        )
