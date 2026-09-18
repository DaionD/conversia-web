"""AMRAS API entry point.

Equivalent to `uvicorn api.app:app --host <API_HOST> --port <API_PORT>`,
reading the host/port from .env so a single `python api_main.py` is enough
for local development.
"""
from __future__ import annotations

import uvicorn

from config.settings import settings

if __name__ == "__main__":
    uvicorn.run("api.app:app", host=settings.api_host, port=settings.api_port, reload=False)
