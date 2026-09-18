"""Runs the AmrasEngine trading loop in a background daemon thread.

The engine talks to the exchange through synchronous CCXT calls, so it
cannot run on the API's asyncio event loop without blocking every request.
A dedicated thread keeps the two fully decoupled: the loop only ever writes
to EngineState, and the API only ever reads from it.
"""
from __future__ import annotations

import logging
import threading

from config.settings import settings
from core.state import EngineState

logger = logging.getLogger("amras.api.runner")


def start_engine_thread(state: EngineState) -> threading.Thread:
    import main as amras_main  # local import: avoids a hard dependency at module load time

    engine = amras_main.build_engine(state=state)
    stop_event = threading.Event()

    def _loop() -> None:
        logger.info(
            "Background engine loop starting: exchange=%s symbols=%s poll=%ss",
            settings.exchange_name, settings.symbol_list, settings.poll_seconds,
        )
        while not stop_event.is_set():
            try:
                engine.run_cycle()
            except Exception:
                logger.exception("Unhandled error in engine cycle")
                state.record_error("Unhandled error in engine cycle -- see server logs")
            stop_event.wait(settings.poll_seconds)

    thread = threading.Thread(target=_loop, name="amras-engine-loop", daemon=True)
    thread.stop_event = stop_event  # type: ignore[attr-defined]
    thread.engine = engine  # type: ignore[attr-defined]
    thread.start()
    return thread
