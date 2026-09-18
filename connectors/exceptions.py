"""Connector exception hierarchy. Core/strategy code only ever catches these,
never a specific exchange SDK's exceptions -- that translation happens
inside each connector implementation.
"""
from __future__ import annotations


class ConnectorError(Exception):
    """Base exception for all exchange/broker connector failures."""


class NetworkError(ConnectorError):
    """Raised on connectivity failures after retries are exhausted."""


class AuthenticationError(ConnectorError):
    """Raised when API credentials are invalid or rejected."""


class InsufficientFundsError(ConnectorError):
    """Raised when the account lacks the balance required for an order."""


class OrderExecutionError(ConnectorError):
    """Raised when an order could not be created, filled, or canceled."""


class UnsupportedExchangeError(ConnectorError):
    """Raised when the requested exchange/broker has no registered connector."""
