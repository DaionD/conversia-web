from __future__ import annotations

from core.enums import MarketRegime, OrderSide, OrderStatus, OrderType, PositionSide, SignalAction
from core.models import OrderResult, Position, Signal
from core.state import EngineState


def _make_signal(i: int) -> Signal:
    return Signal(
        symbol="BTC/USDT", action=SignalAction.BUY, strategy_name="x", regime=MarketRegime.TREND,
        entry_price=100 + i, stop_loss=98, take_profit=105,
    )


def test_snapshot_reflects_equity_and_regime():
    state = EngineState()
    state.set_equity(9999.5)
    state.set_regime("ETH/USDT", MarketRegime.RANGE)
    snap = state.snapshot()
    assert snap.equity == 9999.5
    assert snap.regimes["ETH/USDT"] == MarketRegime.RANGE


def test_position_upsert_and_remove_roundtrip():
    state = EngineState()
    position = Position(
        symbol="BTC/USDT", side=PositionSide.LONG, entry_price=100, amount=1,
        stop_loss=98, take_profit=106, strategy_name="x",
    )
    state.upsert_position(position)
    assert "BTC/USDT" in state.snapshot().positions
    state.remove_position("BTC/USDT")
    assert "BTC/USDT" not in state.snapshot().positions


def test_signal_history_is_capped_at_max_history():
    state = EngineState(max_history=5)
    for i in range(20):
        state.record_signal(_make_signal(i))
    snap = state.snapshot()
    assert len(snap.recent_signals) == 5
    # the most recent ones are kept, not the oldest
    assert snap.recent_signals[-1].entry_price == 119


def test_order_history_is_capped_at_max_history():
    state = EngineState(max_history=3)
    for i in range(10):
        state.record_order(OrderResult(
            order_id=str(i), symbol="BTC/USDT", side=OrderSide.BUY, order_type=OrderType.MARKET,
            status=OrderStatus.FILLED, requested_price=100, filled_price=100,
            amount=1, filled_amount=1,
        ))
    snap = state.snapshot()
    assert len(snap.recent_orders) == 3
    assert [o.order_id for o in snap.recent_orders] == ["7", "8", "9"]


def test_update_status_sets_fields_and_timestamp():
    state = EngineState()
    state.update_status(algorithms_online=True, kill_switch_halted=True)
    status = state.snapshot().status
    assert status.algorithms_online is True
    assert status.kill_switch_halted is True
    assert status.last_cycle_at is not None


def test_record_error_is_visible_in_snapshot():
    state = EngineState()
    state.record_error("boom")
    assert state.snapshot().status.last_error == "boom"
