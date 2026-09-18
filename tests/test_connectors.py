from __future__ import annotations

import pytest

from connectors.exceptions import UnsupportedExchangeError
from connectors.factory import build_connector


def test_build_connector_binance_returns_ccxt_connector():
    connector = build_connector("binance", api_key="x", api_secret="y", sandbox=True)
    assert connector.exchange_id == "binance"


def test_build_connector_is_case_insensitive():
    connector = build_connector("BYBIT", api_key="x", api_secret="y")
    assert connector.exchange_id == "bybit"


def test_build_connector_unsupported_raises():
    with pytest.raises(UnsupportedExchangeError):
        build_connector("not_a_real_exchange", api_key="x", api_secret="y")


def test_build_connector_mt5_returns_stub_not_implemented():
    connector = build_connector("mt5", api_key="x", api_secret="y")
    with pytest.raises(NotImplementedError):
        connector.get_balance()
