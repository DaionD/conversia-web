"""Mean-Reversion engine: RSI oscillator trading overbought/oversold extremes
inside a rolling price channel. Active only while the Regime Engine reports
MarketRegime.RANGE.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

from core import indicators
from core.enums import MarketRegime, SignalAction
from core.models import Signal
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger("amras.strategy.mean_reversion")


@dataclass(slots=True)
class MeanReversionConfig:
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    channel_period: int = 20
    atr_period: int = 14
    atr_sl_multiplier: float = 1.2
    reward_multiplier: float = 1.8


class MeanReversionStrategy(BaseStrategy):
    regime = MarketRegime.RANGE
    name = "mean_reversion_rsi_channel"

    def __init__(self, config: MeanReversionConfig | None = None) -> None:
        self.config = config or MeanReversionConfig()

    def generate_signal(self, ohlcv: pd.DataFrame) -> Signal | None:
        cfg = self.config
        if len(ohlcv) < max(cfg.rsi_period, cfg.channel_period) + 2:
            return None

        rsi = indicators.rsi(ohlcv["close"], cfg.rsi_period)
        atr = indicators.atr(ohlcv, cfg.atr_period)
        channel_high = ohlcv["high"].rolling(cfg.channel_period).max()
        channel_low = ohlcv["low"].rolling(cfg.channel_period).min()

        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]
        price = float(ohlcv["close"].iloc[-1])
        atr_value = float(atr.iloc[-1])

        if pd.isna(current_rsi) or pd.isna(prev_rsi) or pd.isna(atr_value) or atr_value <= 0:
            return None

        mid_channel = (channel_high.iloc[-1] + channel_low.iloc[-1]) / 2

        long_trigger = prev_rsi <= cfg.rsi_oversold < current_rsi
        short_trigger = prev_rsi >= cfg.rsi_overbought > current_rsi

        if not long_trigger and not short_trigger:
            return None

        confidence = min(abs(current_rsi - 50) / 50, 1.0)

        if long_trigger:
            stop_loss = price - atr_value * cfg.atr_sl_multiplier
            take_profit = max(mid_channel, price + atr_value * cfg.atr_sl_multiplier * cfg.reward_multiplier)
            action = SignalAction.BUY
        else:
            stop_loss = price + atr_value * cfg.atr_sl_multiplier
            take_profit = min(mid_channel, price - atr_value * cfg.atr_sl_multiplier * cfg.reward_multiplier)
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
                "rsi": float(current_rsi),
                "channel_high": float(channel_high.iloc[-1]),
                "channel_low": float(channel_low.iloc[-1]),
            },
        )
