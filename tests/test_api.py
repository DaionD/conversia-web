from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.app import app, state
from core.enums import MarketRegime, OrderSide, OrderStatus, OrderType, PositionSide, SignalAction
from core.models import OrderResult, Position, Signal


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["engine_running"] is False  # API_RUN_ENGINE defaults to false


def test_status_defaults_before_any_cycle(client):
    resp = client.get("/api/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["algorithms_online"] is False
    assert body["kill_switch_halted"] is False


def test_portfolio_reflects_state(client):
    state.set_equity(12345.67)
    resp = client.get("/api/portfolio")
    assert resp.json()["equity"] == 12345.67


def test_regime_endpoint(client):
    state.set_regime("BTC/USDT", MarketRegime.TREND)
    resp = client.get("/api/regime")
    assert {"symbol": "BTC/USDT", "regime": "trend"} in resp.json()


def test_positions_endpoint_includes_unrealized_pnl(client):
    position = Position(
        symbol="ETH/USDT", side=PositionSide.LONG, entry_price=3000, amount=1,
        stop_loss=2950, take_profit=3100, strategy_name="trend_following_ma_crossover",
    )
    state.upsert_position(position)
    state.set_price("ETH/USDT", 3050)
    try:
        resp = client.get("/api/positions")
        match = next(p for p in resp.json() if p["symbol"] == "ETH/USDT")
        assert match["unrealized_pnl"] == pytest.approx(50.0)
    finally:
        state.remove_position("ETH/USDT")


def test_recent_signals_endpoint(client):
    signal = Signal(
        symbol="BTC/USDT", action=SignalAction.BUY, strategy_name="trend_following_ma_crossover",
        regime=MarketRegime.TREND, entry_price=60000, stop_loss=59000, take_profit=62000,
        confidence=0.8,
    )
    state.record_signal(signal)
    resp = client.get("/api/signals/recent")
    assert any(s["symbol"] == "BTC/USDT" and s["action"] == "buy" for s in resp.json())


def test_recent_orders_endpoint(client):
    order = OrderResult(
        order_id="abc123", symbol="BTC/USDT", side=OrderSide.BUY, order_type=OrderType.MARKET,
        status=OrderStatus.FILLED, requested_price=60000, filled_price=60010,
        amount=0.1, filled_amount=0.1, fee=0.6, fee_currency="USDT",
    )
    state.record_order(order)
    resp = client.get("/api/orders/recent")
    data = resp.json()
    match = next(o for o in data if o["order_id"] == "abc123")
    assert match["slippage"] == pytest.approx(10.0)


def test_websocket_stream_sends_snapshot(client):
    with client.websocket_connect("/ws/stream") as ws:
        msg = ws.receive_json()
        assert "equity" in msg
        assert "status" in msg
        assert "regimes" in msg
