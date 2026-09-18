"""AMRAS top-level orchestrator: regime detection -> strategy selection ->
risk validation -> execution -> active position management.
"""
from __future__ import annotations

import logging
import time
from typing import Sequence

import pandas as pd

from connectors.base_connector import BaseExchangeConnector
from connectors.exceptions import ConnectorError
from core import indicators
from core.enums import MarketRegime, OrderSide, OrderType, PositionSide, SignalAction
from core.models import OrderRequest, Position, Signal
from core.order_manager import OrderManager
from core.regime_engine import RegimeEngine
from core.risk_manager import KillSwitchActive, RiskManager
from core.state import EngineState
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger("amras.engine")


class AmrasEngine:
    def __init__(
        self,
        connector: BaseExchangeConnector,
        strategies: Sequence[BaseStrategy],
        regime_engine: RegimeEngine,
        risk_manager: RiskManager,
        symbols: Sequence[str],
        timeframe: str = "1h",
        state: EngineState | None = None,
    ) -> None:
        self.connector = connector
        self.order_manager = OrderManager(connector)
        self.strategies: dict[MarketRegime, BaseStrategy] = {s.regime: s for s in strategies}
        self.regime_engine = regime_engine
        self.risk_manager = risk_manager
        self.symbols = list(symbols)
        self.timeframe = timeframe
        self.open_positions: dict[str, Position] = {}
        self.state = state

    def run_cycle(self) -> None:
        try:
            equity = self.connector.get_balance().total
        except ConnectorError as exc:
            logger.error("Cycle aborted: could not fetch balance: %s", exc)
            if self.state:
                self.state.update_status(broker_connected=False, data_feed_online=False)
                self.state.record_error(str(exc))
            return

        self.risk_manager.register_equity(equity)
        if self.state:
            self.state.set_equity(equity)

        try:
            self.risk_manager.ensure_trading_allowed()
        except KillSwitchActive as exc:
            logger.warning("Cycle skipped: %s", exc)
            if self.state:
                self.state.update_status(
                    algorithms_online=True, broker_connected=True, data_feed_online=True,
                    risk_engine_active=True, kill_switch_halted=True,
                )
            return

        if self.state:
            self.state.update_status(
                algorithms_online=True, broker_connected=True, data_feed_online=True,
                risk_engine_active=True, kill_switch_halted=False,
            )

        for symbol in self.symbols:
            try:
                self._process_symbol(symbol, equity)
            except Exception as exc:
                logger.exception("Error processing symbol %s", symbol)
                if self.state:
                    self.state.record_error(f"{symbol}: {exc}")

    def _process_symbol(self, symbol: str, equity: float) -> None:
        candles = self.connector.get_historical_klines(symbol, self.timeframe, limit=250)
        df = pd.DataFrame([c.__dict__ for c in candles])
        df.attrs["symbol"] = symbol

        regime = self.regime_engine.classify(df)
        if self.state:
            self.state.set_regime(symbol, regime)
            self.state.set_price(symbol, float(df["close"].iloc[-1]))

        if symbol in self.open_positions:
            self._manage_open_position(symbol, df)

        strategy = self.strategies.get(regime)
        if strategy is None:
            logger.debug("No strategy mapped to regime %s for %s", regime, symbol)
            return

        if symbol in self.open_positions:
            return  # one position per symbol at a time

        signal = strategy.generate_signal(df)
        if signal is None or signal.action == SignalAction.HOLD:
            return

        if not self.risk_manager.validate_signal(signal):
            return

        if self.state:
            self.state.record_signal(signal)

        self._execute_signal(signal, equity)

    def _execute_signal(self, signal: Signal, equity: float) -> None:
        size = self.risk_manager.calculate_position_size(equity, signal.entry_price, signal.stop_loss)
        side = OrderSide.BUY if signal.action == SignalAction.BUY else OrderSide.SELL

        if signal.regime == MarketRegime.VOLATILITY_COMPRESSION:
            # Breakout signals are pending stop orders at the trigger level.
            request = OrderRequest(
                symbol=signal.symbol, side=side, order_type=OrderType.STOP_MARKET,
                amount=size, stop_price=signal.entry_price,
            )
        else:
            request = OrderRequest(
                symbol=signal.symbol, side=side, order_type=OrderType.MARKET,
                amount=size, price=signal.entry_price,
            )

        result = self.order_manager.submit(request)
        if self.state:
            self.state.record_order(result)

        position_side = PositionSide.LONG if side == OrderSide.BUY else PositionSide.SHORT
        position = Position(
            symbol=signal.symbol,
            side=position_side,
            entry_price=result.filled_price or signal.entry_price,
            amount=result.filled_amount or size,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            strategy_name=signal.strategy_name,
            initial_risk=abs(signal.entry_price - signal.stop_loss),
        )
        self.open_positions[signal.symbol] = position
        if self.state:
            self.state.upsert_position(position)
        logger.info("Opened %s position on %s via %s", position_side, signal.symbol, signal.strategy_name)

    def _manage_open_position(self, symbol: str, df: pd.DataFrame) -> None:
        position = self.open_positions[symbol]
        current_price = float(df["close"].iloc[-1])
        atr_value = float(indicators.atr(df, self.risk_manager.config.atr_period).iloc[-1])

        self.risk_manager.apply_breakeven(position, current_price)
        self.risk_manager.apply_trailing_stop(position, current_price, atr_value)

        hit_stop = (
            current_price <= position.stop_loss if position.side == PositionSide.LONG
            else current_price >= position.stop_loss
        )
        hit_target = (
            current_price >= position.take_profit if position.side == PositionSide.LONG
            else current_price <= position.take_profit
        )
        if hit_stop or hit_target:
            self._close_position(symbol, current_price, reason="stop_loss" if hit_stop else "take_profit")

    def _close_position(self, symbol: str, price: float, reason: str) -> None:
        position = self.open_positions.pop(symbol)
        if self.state:
            self.state.remove_position(symbol)
        side = OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY
        request = OrderRequest(symbol=symbol, side=side, order_type=OrderType.MARKET, amount=position.amount, price=price)
        result = self.order_manager.submit(request)
        if self.state:
            self.state.record_order(result)
        logger.info("Closed %s position on %s (%s) at %.6f", position.side, symbol, reason, price)

    def run_forever(self, poll_seconds: int = 60) -> None:
        logger.info("AMRAS engine starting main loop (poll every %ss)", poll_seconds)
        while True:
            self.run_cycle()
            time.sleep(poll_seconds)
