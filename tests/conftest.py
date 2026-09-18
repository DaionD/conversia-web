from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def _make_ohlcv(closes: np.ndarray, start_price: float = 100.0) -> pd.DataFrame:
    n = len(closes)
    highs = closes * 1.002
    lows = closes * 0.998
    opens = np.roll(closes, 1)
    opens[0] = start_price
    volumes = np.full(n, 1000.0)
    return pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes})


@pytest.fixture
def trending_ohlcv() -> pd.DataFrame:
    closes = 100 + np.cumsum(np.full(300, 0.6))
    return _make_ohlcv(closes)


@pytest.fixture
def ranging_ohlcv() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    closes = 100 + np.sin(np.linspace(0, 20 * np.pi, 300)) * 2 + rng.normal(0, 0.1, 300)
    return _make_ohlcv(closes)


@pytest.fixture
def compressed_ohlcv() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    closes = 100 + rng.normal(0, 0.02, 300)
    return _make_ohlcv(closes)
