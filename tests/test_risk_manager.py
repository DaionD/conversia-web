from __future__ import annotations

import pytest

from core.enums import MarketRegime, PositionSide, SignalAction
from core.models import Position, Signal
from core.risk_manager import KillSwitchActive, RiskConfig, RiskManager


def test_position_sizing_respects_risk_percent():
    rm = RiskManager(RiskConfig(risk_per_trade_pct=1.0))
    size = rm.calculate_position_size(equity=10_000, entry_price=100, stop_loss=98)
    assert size == pytest.approx(50.0)  # (10_000 * 1%) / 2 stop distance


def test_position_sizing_rejects_zero_stop_distance():
    rm = RiskManager()
    with pytest.raises(ValueError):
        rm.calculate_position_size(equity=10_000, entry_price=100, stop_loss=100)


def test_rejects_signal_below_min_rr():
    rm = RiskManager(RiskConfig(min_risk_reward=2.0))
    signal = Signal(
        symbol="BTC/USDT", action=SignalAction.BUY, strategy_name="x", regime=MarketRegime.TREND,
        entry_price=100, stop_loss=98, take_profit=102,
    )
    assert rm.validate_signal(signal) is False


def test_accepts_signal_meeting_min_rr():
    rm = RiskManager(RiskConfig(min_risk_reward=1.5))
    signal = Signal(
        symbol="BTC/USDT", action=SignalAction.BUY, strategy_name="x", regime=MarketRegime.TREND,
        entry_price=100, stop_loss=98, take_profit=105,
    )
    assert rm.validate_signal(signal) is True


def test_breakeven_moves_stop_to_entry():
    rm = RiskManager(RiskConfig(breakeven_trigger_rr=1.0))
    position = Position(
        symbol="BTC/USDT", side=PositionSide.LONG, entry_price=100, amount=1,
        stop_loss=98, take_profit=106, strategy_name="x",
    )
    assert rm.apply_breakeven(position, current_price=102) is True
    assert position.stop_loss == 100


def test_trailing_stop_only_moves_in_favorable_direction():
    rm = RiskManager(RiskConfig(atr_trailing_multiplier=1.0))
    position = Position(
        symbol="BTC/USDT", side=PositionSide.LONG, entry_price=100, amount=1,
        stop_loss=95, take_profit=110, strategy_name="x",
    )
    assert rm.apply_trailing_stop(position, current_price=105, atr_value=2.0) is True
    assert position.stop_loss == pytest.approx(103.0)
    # A pullback must never drag the stop back down.
    assert rm.apply_trailing_stop(position, current_price=101, atr_value=2.0) is False
    assert position.stop_loss == pytest.approx(103.0)


def test_kill_switch_blocks_trading_after_drawdown_breach():
    rm = RiskManager(RiskConfig(max_daily_drawdown_pct=3.0))
    rm.start_of_day(equity=10_000)
    rm.register_equity(9_650)  # -3.5% drawdown
    assert rm.is_trading_allowed is False
    with pytest.raises(KillSwitchActive):
        rm.ensure_trading_allowed()


def test_kill_switch_stays_off_within_drawdown_limit():
    rm = RiskManager(RiskConfig(max_daily_drawdown_pct=3.0))
    rm.start_of_day(equity=10_000)
    rm.register_equity(9_800)  # -2% drawdown
    assert rm.is_trading_allowed is True
