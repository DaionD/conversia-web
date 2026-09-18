"""Centralized, typed configuration for AMRAS.

All runtime parameters are loaded from environment variables (via a local
.env file). To switch broker/exchange, strategy tuning, or risk limits the
user only needs to edit `.env` -- no code changes are required anywhere
else in the system.
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- exchange / broker selection -------------------------------------
    exchange_name: str = "binance"
    api_key: str = ""
    api_secret: str = ""
    api_password: str = ""  # required by OKX / KuCoin / Bitget (passphrase)
    sandbox_mode: bool = True

    # --- market scope -------------------------------------------------
    symbols: str = "BTC/USDT,ETH/USDT"
    timeframe: str = "1h"
    poll_seconds: int = 60

    # --- regime-switching engine -------------------------------------------------
    adx_period: int = 14
    adx_trend_threshold: float = 25.0
    atr_period: int = 14
    bandwidth_period: int = 20
    bandwidth_compression_percentile: float = 0.20

    # --- strategy parameters -------------------------------------------------
    ma_fast_period: int = 50
    ma_slow_period: int = 200
    adx_min_strength: float = 20.0
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    breakout_lookback_period: int = 20

    # --- risk engine -------------------------------------------------
    risk_per_trade_pct: float = 0.75
    min_risk_reward: float = 1.5
    atr_sl_multiplier: float = 1.5
    atr_trailing_multiplier: float = 2.0
    breakeven_trigger_rr: float = 1.0
    max_daily_drawdown_pct: float = 3.0
    kill_switch_cooldown_hours: int = 24

    # --- logging -------------------------------------------------
    log_level: str = "INFO"

    # --- API layer -------------------------------------------------
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_run_engine: bool = False
    cors_origins: str = "*"
    ws_broadcast_interval_seconds: float = 2.0

    @property
    def symbol_list(self) -> list[str]:
        return [s.strip() for s in self.symbols.split(",") if s.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
