"""Connector factory: the single switch point that lets the user change
broker/exchange by editing one variable (EXCHANGE_NAME) in .env, with no
code changes required anywhere else in the system.
"""
from __future__ import annotations

import importlib

from connectors.base_connector import BaseExchangeConnector
from connectors.exceptions import UnsupportedExchangeError

_NATIVE_BROKERS = {"mt5", "interactive_brokers"}


def build_connector(
    exchange_name: str,
    api_key: str,
    api_secret: str,
    api_password: str = "",
    sandbox: bool = False,
) -> BaseExchangeConnector:
    name = exchange_name.lower().strip()

    if name == "mt5":
        from connectors.mt5_connector import MT5Connector

        return MT5Connector(api_key, api_secret)

    if name == "interactive_brokers":
        from connectors.ib_connector import IBConnector

        return IBConnector(api_key, api_secret)

    try:
        ccxt = importlib.import_module("ccxt")
    except ImportError as exc:
        raise UnsupportedExchangeError("ccxt is not installed; run `pip install -r requirements.txt`") from exc

    if not hasattr(ccxt, name):
        raise UnsupportedExchangeError(
            f"'{exchange_name}' is not a recognized CCXT exchange id or native broker "
            f"({sorted(_NATIVE_BROKERS)})."
        )

    from connectors.ccxt_connector import CCXTConnector

    return CCXTConnector(
        exchange_id=name,
        api_key=api_key,
        api_secret=api_secret,
        password=api_password,
        sandbox=sandbox,
    )
