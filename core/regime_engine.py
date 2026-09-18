"""Regime-Switching Engine: classifies the market before every decision cycle."""
from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

from core import indicators
from core.enums import MarketRegime

logger = logging.getLogger("amras.regime")


@dataclass(slots=True)
class RegimeThresholds:
    adx_period: int = 14
    atr_period: int = 14
    adx_trend_threshold: float = 25.0
    bandwidth_period: int = 20
    bandwidth_compression_percentile: float = 0.20  # bottom 20% of recent bandwidth = compression


class RegimeEngine:
    """Classifies the current market state into TREND, RANGE or VOLATILITY_COMPRESSION.

    ADX drives the trend/no-trend split; when the market isn't trending, the
    Bollinger bandwidth percentile rank decides between a tight compression
    (candidate for a breakout) and a normal range (mean-reversion).
    """

    def __init__(self, thresholds: RegimeThresholds | None = None) -> None:
        self.thresholds = thresholds or RegimeThresholds()

    def classify(self, ohlcv: pd.DataFrame) -> MarketRegime:
        t = self.thresholds
        min_required = max(t.adx_period, t.bandwidth_period) * 2
        if len(ohlcv) < min_required:
            logger.warning(
                "Insufficient candles (%d < %d) to classify regime, defaulting to UNKNOWN",
                len(ohlcv), min_required,
            )
            return MarketRegime.UNKNOWN

        adx_series = indicators.adx(ohlcv, t.adx_period)
        bandwidth = indicators.bollinger_bandwidth(ohlcv["close"], t.bandwidth_period)

        current_adx = adx_series.iloc[-1]
        current_bandwidth = bandwidth.iloc[-1]
        bandwidth_rank = bandwidth.rank(pct=True).iloc[-1]

        if pd.isna(current_adx) or pd.isna(current_bandwidth):
            return MarketRegime.UNKNOWN

        if current_adx >= t.adx_trend_threshold:
            regime = MarketRegime.TREND
        elif bandwidth_rank <= t.bandwidth_compression_percentile:
            regime = MarketRegime.VOLATILITY_COMPRESSION
        else:
            regime = MarketRegime.RANGE

        logger.info(
            "Regime classified: %s (ADX=%.2f, bandwidth=%.4f, bandwidth_rank=%.2f)",
            regime, current_adx, current_bandwidth, bandwidth_rank,
        )
        return regime
