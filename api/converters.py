"""Domain -> API schema conversion helpers."""
from __future__ import annotations

from core.models import OrderResult, Position, Signal
from api.schemas import OrderOut, PositionOut, SignalOut


def position_to_schema(position: Position, last_price: float | None) -> PositionOut:
    return PositionOut(
        symbol=position.symbol,
        side=position.side.value,
        entry_price=position.entry_price,
        amount=position.amount,
        stop_loss=position.stop_loss,
        take_profit=position.take_profit,
        strategy_name=position.strategy_name,
        opened_at=position.opened_at,
        breakeven_applied=position.breakeven_applied,
        trailing_active=position.trailing_active,
        last_price=last_price,
        unrealized_pnl=position.unrealized_pnl(last_price) if last_price is not None else None,
    )


def signal_to_schema(signal: Signal) -> SignalOut:
    return SignalOut(
        symbol=signal.symbol,
        action=signal.action.value,
        strategy_name=signal.strategy_name,
        regime=signal.regime.value,
        entry_price=signal.entry_price,
        stop_loss=signal.stop_loss,
        take_profit=signal.take_profit,
        confidence=signal.confidence,
        risk_reward_ratio=signal.risk_reward_ratio,
        generated_at=signal.generated_at,
    )


def order_to_schema(order: OrderResult) -> OrderOut:
    return OrderOut(
        order_id=order.order_id,
        symbol=order.symbol,
        side=order.side.value,
        order_type=order.order_type.value,
        status=order.status.value,
        requested_price=order.requested_price,
        filled_price=order.filled_price,
        amount=order.amount,
        filled_amount=order.filled_amount,
        fee=order.fee,
        fee_currency=order.fee_currency,
        slippage=order.slippage,
        latency_ms=order.latency_ms,
        timestamp=order.timestamp,
    )
