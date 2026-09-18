from __future__ import annotations

import pandas as pd

from core.enums import MarketRegime
from core.regime_engine import RegimeEngine


def test_classifies_trend(trending_ohlcv):
    engine = RegimeEngine()
    assert engine.classify(trending_ohlcv) == MarketRegime.TREND


def test_classifies_compression_or_range(compressed_ohlcv):
    engine = RegimeEngine()
    regime = engine.classify(compressed_ohlcv)
    assert regime in (MarketRegime.VOLATILITY_COMPRESSION, MarketRegime.RANGE)


def test_insufficient_data_returns_unknown():
    engine = RegimeEngine()
    tiny_df = pd.DataFrame({"open": [1, 2], "high": [1, 2], "low": [1, 2], "close": [1, 2], "volume": [1, 1]})
    assert engine.classify(tiny_df) == MarketRegime.UNKNOWN
