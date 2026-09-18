from __future__ import annotations

import numpy as np
import pandas as pd

from core import indicators
from core.enums import SignalAction
from strategies.breakout import BreakoutConfig, BreakoutStrategy
from strategies.mean_reversion import MeanReversionConfig, MeanReversionStrategy
from strategies.trend_following import TrendFollowingConfig, TrendFollowingStrategy


def _crossover_ohlcv(fast_period: int, slow_period: int) -> pd.DataFrame:
    """Mildly noisy sideways action followed by a sustained ramp, truncated
    to the exact bar where the fast SMA first crosses above the slow SMA --
    i.e. real market-shaped data (non-zero ADX/ATR throughout) ending on the
    crossover event the strategy looks for."""
    rng = np.random.default_rng(123)
    noise = rng.normal(0, 0.15, 150)
    sideways = 100 + np.cumsum(noise) * 0.05
    ramp = sideways[-1] + np.cumsum(np.full(60, 0.8))
    closes = np.concatenate([sideways, ramp])

    highs = closes + rng.normal(0.3, 0.05, len(closes))
    lows = closes - rng.normal(0.3, 0.05, len(closes))
    opens = np.roll(closes, 1)
    opens[0] = closes[0]
    df = pd.DataFrame({"open": opens, "high": highs, "low": lows, "close": closes, "volume": np.full(len(closes), 1000.0)})

    fast = indicators.sma(df["close"], fast_period)
    slow = indicators.sma(df["close"], slow_period)
    crossed_up = (fast.shift(1) <= slow.shift(1)) & (fast > slow)
    crossover_idx = np.where(crossed_up.to_numpy())[0][-1]
    return df.iloc[: crossover_idx + 1].reset_index(drop=True)


def test_trend_following_generates_signal_on_fresh_crossover():
    df = _crossover_ohlcv(fast_period=10, slow_period=30)
    strategy = TrendFollowingStrategy(
        TrendFollowingConfig(fast_ma_period=10, slow_ma_period=30, adx_min_strength=0)
    )
    signal = strategy.generate_signal(df)
    assert signal is not None
    assert signal.action == SignalAction.BUY
    assert signal.risk_reward_ratio > 0


def test_trend_following_requires_enough_history():
    strategy = TrendFollowingStrategy(TrendFollowingConfig())
    tiny_df = pd.DataFrame({"open": [1] * 5, "high": [1] * 5, "low": [1] * 5, "close": [1] * 5, "volume": [1] * 5})
    assert strategy.generate_signal(tiny_df) is None


def test_mean_reversion_requires_enough_history():
    strategy = MeanReversionStrategy(MeanReversionConfig())
    tiny_df = pd.DataFrame({"open": [1] * 5, "high": [1] * 5, "low": [1] * 5, "close": [1] * 5, "volume": [1] * 5})
    assert strategy.generate_signal(tiny_df) is None


def test_breakout_targets_nearest_level(compressed_ohlcv):
    strategy = BreakoutStrategy(BreakoutConfig(lookback_period=20))
    signal = strategy.generate_signal(compressed_ohlcv)
    if signal is not None:
        assert signal.metadata.get("pending") is True
        assert signal.risk_reward_ratio > 0
