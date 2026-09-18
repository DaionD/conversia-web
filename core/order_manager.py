"""Order execution orchestration: submits orders through a connector and
records execution telemetry (slippage, fees, latency) to the audit log.
"""
from __future__ import annotations

import logging
import time

from connectors.base_connector import BaseExchangeConnector
from connectors.exceptions import OrderExecutionError
from core.models import OrderRequest, OrderResult

execution_logger = logging.getLogger("amras.execution")


class OrderManager:
    """Coordinates order submission through a connector and records execution telemetry."""

    def __init__(self, connector: BaseExchangeConnector) -> None:
        self.connector = connector

    def submit(self, request: OrderRequest) -> OrderResult:
        start = time.perf_counter()
        try:
            result = self.connector.create_order(request)
        except Exception as exc:
            execution_logger.error("Order submission failed for %s: %s", request.symbol, exc)
            raise OrderExecutionError(str(exc)) from exc

        result.latency_ms = (time.perf_counter() - start) * 1000

        execution_logger.info(
            "ORDER %s | %s %s %.6f @ %s | status=%s filled=%.6f fee=%.6f %s | "
            "slippage=%s | latency=%.1fms",
            result.order_id, request.side, request.order_type, request.amount,
            request.price, result.status, result.filled_amount, result.fee,
            result.fee_currency, result.slippage, result.latency_ms,
        )
        return result

    def cancel(self, symbol: str, order_id: str) -> bool:
        try:
            return self.connector.cancel_order(symbol, order_id)
        except Exception as exc:
            execution_logger.error("Cancel failed for order %s (%s): %s", order_id, symbol, exc)
            raise OrderExecutionError(str(exc)) from exc
