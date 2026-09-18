"""AMRAS entry point.

Wires configuration, logging, the connector (selected via EXCHANGE_NAME in
.env), the regime engine, the risk engine and the three tactical strategies
into a single AmrasEngine, then runs the main polling loop until a shutdown
signal (SIGINT/SIGTERM) is received.
"""
from __future__ import annotations

import logging
import signal
import sys
import time

from config.logging_config import configure_logging
from config.settings import settings
from connectors.factory import build_connector
from core.engine import AmrasEngine
from core.regime_engine import RegimeEngine, RegimeThresholds
from core.risk_manager import RiskConfig, RiskManager
from core.state import EngineState
from strategies.breakout import BreakoutConfig, BreakoutStrategy
from strategies.mean_reversion import MeanReversionConfig, MeanReversionStrategy
from strategies.trend_following import TrendFollowingConfig, TrendFollowingStrategy

logger = logging.getLogger("amras.main")

_shutdown_requested = False


def _handle_shutdown(signum, frame) -> None:
    global _shutdown_requested
    logger.info("Shutdown signal received (%s). Finishing current cycle...", signum)
    _shutdown_requested = True


def build_engine(state: EngineState | None = None) -> AmrasEngine:
    connector = build_connector(
        exchange_name=settings.exchange_name,
        api_key=settings.api_key,
        api_secret=settings.api_secret,
        api_password=settings.api_password,
        sandbox=settings.sandbox_mode,
    )

    regime_engine = RegimeEngine(
        RegimeThresholds(
            adx_period=settings.adx_period,
            atr_period=settings.atr_period,
            adx_trend_threshold=settings.adx_trend_threshold,
            bandwidth_period=settings.bandwidth_period,
            bandwidth_compression_percentile=settings.bandwidth_compression_percentile,
        )
    )

    risk_manager = RiskManager(
        RiskConfig(
            risk_per_trade_pct=settings.risk_per_trade_pct,
            min_risk_reward=settings.min_risk_reward,
            atr_period=settings.atr_period,
            atr_sl_multiplier=settings.atr_sl_multiplier,
            atr_trailing_multiplier=settings.atr_trailing_multiplier,
            breakeven_trigger_rr=settings.breakeven_trigger_rr,
            max_daily_drawdown_pct=settings.max_daily_drawdown_pct,
            kill_switch_cooldown_hours=settings.kill_switch_cooldown_hours,
        )
    )

    strategies = [
        TrendFollowingStrategy(TrendFollowingConfig(
            fast_ma_period=settings.ma_fast_period,
            slow_ma_period=settings.ma_slow_period,
            adx_period=settings.adx_period,
            adx_min_strength=settings.adx_min_strength,
            atr_period=settings.atr_period,
        )),
        MeanReversionStrategy(MeanReversionConfig(
            rsi_period=settings.rsi_period,
            rsi_overbought=settings.rsi_overbought,
            rsi_oversold=settings.rsi_oversold,
            atr_period=settings.atr_period,
        )),
        BreakoutStrategy(BreakoutConfig(
            lookback_period=settings.breakout_lookback_period,
            atr_period=settings.atr_period,
        )),
    ]

    return AmrasEngine(
        connector=connector,
        strategies=strategies,
        regime_engine=regime_engine,
        risk_manager=risk_manager,
        symbols=settings.symbol_list,
        timeframe=settings.timeframe,
        state=state,
    )


def main() -> int:
    configure_logging()
    logger.info("Starting AMRAS (Adaptive Market-Regime Algorithmic System)")
    logger.info(
        "Exchange: %s | Symbols: %s | Timeframe: %s | Sandbox: %s",
        settings.exchange_name, settings.symbol_list, settings.timeframe, settings.sandbox_mode,
    )

    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    engine = build_engine()
    try:
        while not _shutdown_requested:
            engine.run_cycle()
            slept = 0
            while slept < settings.poll_seconds and not _shutdown_requested:
                time.sleep(1)
                slept += 1
    finally:
        engine.connector.close()
        logger.info("AMRAS stopped cleanly")

    return 0


if __name__ == "__main__":
    sys.exit(main())
