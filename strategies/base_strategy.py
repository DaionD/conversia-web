"""Abstract base for all tactical engines."""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from core.enums import MarketRegime
from core.models import Signal


class BaseStrategy(ABC):
    """Each strategy is bound to exactly one market regime (`regime`) and is
    only ever invoked by the engine while that regime is active."""

    regime: MarketRegime
    name: str

    @abstractmethod
    def generate_signal(self, ohlcv: pd.DataFrame) -> Signal | None:
        """Analyze the latest OHLCV window and return a Signal, or None if there is no setup."""
        raise NotImplementedError
