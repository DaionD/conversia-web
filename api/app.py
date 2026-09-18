"""AMRAS API: serves the live engine state over REST and WebSocket.

All reads come from the in-memory EngineState snapshot published by the
trading loop (see core/state.py, core/engine.py, api/engine_runner.py) --
no endpoint here ever makes a network call to the exchange itself, so
request latency is independent of exchange latency.

Run with:  uvicorn api.app:app --host 0.0.0.0 --port 8000
or:        python api_main.py
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from api.converters import order_to_schema, position_to_schema, signal_to_schema
from api.schemas import HealthOut, PortfolioOut, RegimeOut, SystemStatusOut
from config.logging_config import configure_logging
from config.settings import settings
from core.state import EngineState

configure_logging()
logger = logging.getLogger("amras.api")

state = EngineState()
_engine_thread = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _engine_thread
    if settings.api_run_engine:
        from api.engine_runner import start_engine_thread
        _engine_thread = start_engine_thread(state)
    else:
        logger.info(
            "API_RUN_ENGINE is false: serving the API without a live engine loop "
            "(state will stay empty until enabled)."
        )
    yield


app = FastAPI(
    title="AMRAS API",
    version="1.0.0",
    description="Adaptive Market-Regime Algorithmic System -- control API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut(
        status="ok",
        engine_running=_engine_thread is not None and _engine_thread.is_alive(),
    )


@app.get("/api/status", response_model=SystemStatusOut)
def get_status() -> SystemStatusOut:
    s = state.snapshot().status
    return SystemStatusOut(
        algorithms_online=s.algorithms_online,
        data_feed_online=s.data_feed_online,
        broker_connected=s.broker_connected,
        risk_engine_active=s.risk_engine_active,
        kill_switch_halted=s.kill_switch_halted,
        last_cycle_at=s.last_cycle_at,
        last_error=s.last_error,
    )


@app.get("/api/portfolio", response_model=PortfolioOut)
def get_portfolio() -> PortfolioOut:
    return PortfolioOut(equity=state.snapshot().equity)


@app.get("/api/regime", response_model=list[RegimeOut])
def get_regime() -> list[RegimeOut]:
    snap = state.snapshot()
    return [RegimeOut(symbol=symbol, regime=regime.value) for symbol, regime in snap.regimes.items()]


@app.get("/api/positions", response_model=list[dict])
def get_positions() -> list[dict]:
    snap = state.snapshot()
    return [
        position_to_schema(position, snap.last_prices.get(symbol)).model_dump()
        for symbol, position in snap.positions.items()
    ]


@app.get("/api/signals/recent", response_model=list[dict])
def get_recent_signals(limit: int = 20) -> list[dict]:
    snap = state.snapshot()
    return [signal_to_schema(s).model_dump() for s in snap.recent_signals[-limit:]]


@app.get("/api/orders/recent", response_model=list[dict])
def get_recent_orders(limit: int = 20) -> list[dict]:
    snap = state.snapshot()
    return [order_to_schema(o).model_dump() for o in snap.recent_orders[-limit:]]


@app.websocket("/ws/stream")
async def stream(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            snap = state.snapshot()
            await websocket.send_json({
                "equity": snap.equity,
                "regimes": {symbol: regime.value for symbol, regime in snap.regimes.items()},
                "last_prices": snap.last_prices,
                "positions": {
                    symbol: position_to_schema(position, snap.last_prices.get(symbol)).model_dump(mode="json")
                    for symbol, position in snap.positions.items()
                },
                "status": {
                    "algorithms_online": snap.status.algorithms_online,
                    "broker_connected": snap.status.broker_connected,
                    "kill_switch_halted": snap.status.kill_switch_halted,
                    "last_error": snap.status.last_error,
                },
            })
            await asyncio.sleep(settings.ws_broadcast_interval_seconds)
    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected from /ws/stream")
