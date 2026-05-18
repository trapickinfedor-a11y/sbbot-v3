"""
Сервис начисления заработка воркерам при завершении заказа.
Логика: fixed_price > commission_percent > 100% от order price.
"""

import logging
from decimal import Decimal
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import Worker, Order, BulkOrderItem
from shared.services.ledger_service import LedgerService

logger = logging.getLogger(__name__)


def calculate_order_income_for_worker(order: Order, bulk_items: Optional[List[BulkOrderItem]] = None) -> Decimal:
    """
    Рассчитать доход от заказа (для single/bulk с учётом NF).
    """
    if not order.is_bulk:
        return order.price

    if bulk_items is None:
        bulk_items = getattr(order, "bulk_items", []) or []

    done_count = sum(1 for item in bulk_items if getattr(item, "status", None) == "done")
    if done_count == 0:
        return Decimal("0")

    price_per_item = order.price / order.bulk_count
    return (price_per_item * done_count).quantize(Decimal("0.01"))


def get_worker_score_multiplier(worker: Worker) -> Decimal:
    """
    Returns earnings multiplier based on Worker Score:
    - Score > 4.8: +5% bonus (multiplier 1.05)
    - Score < 3.5: -5% penalty (multiplier 0.95) → share drops from 80% to 75% effectively
    - Otherwise: 1.0 (no change)
    """
    score = float(getattr(worker, "worker_score", 0) or 0)
    if score >= 4.8:
        return Decimal("1.05")
    if 0 < score < 3.5:
        return Decimal("0.95")
    return Decimal("1.0")


def calculate_worker_earnings_from_order(
    order_income: Decimal,
    worker: Worker,
    apply_score_bonus: bool = True,
) -> Decimal:
    """
    Рассчитать сумму к начислению воркеру.
    Приоритет: fixed_price > commission_percent > 100%
    Worker Score multiplier: +5% for score>4.8, -5% for score<3.5
    """
    if worker.fixed_price is not None and float(worker.fixed_price) > 0:
        base = worker.fixed_price
    elif worker.commission_percent is not None and worker.commission_percent > 0:
        pct = Decimal(str(worker.commission_percent)) / Decimal("100")
        base = (order_income * pct)
    else:
        base = order_income

    if apply_score_bonus:
        multiplier = get_worker_score_multiplier(worker)
        base = base * multiplier

    return base.quantize(Decimal("0.01"))


async def credit_worker_on_order_complete(
    session: AsyncSession,
    worker_id: int,
    order: Order,
    bulk_items: Optional[List[BulkOrderItem]] = None,
    order_income_override: Optional[Decimal] = None,
) -> Decimal:
    """
    Начислить воркеру заработок при завершении заказа.
    order_income_override: если задан (напр. из result_data bulk), использовать вместо расчёта.
    Возвращает начисленную сумму.
    """
    worker_res = await session.execute(select(Worker).where(Worker.id == worker_id))
    worker = worker_res.scalar_one_or_none()
    if not worker:
        logger.warning(f"Worker {worker_id} not found, skip earnings")
        return Decimal("0")

    if order_income_override is not None:
        order_income = order_income_override
    else:
        order_income = calculate_order_income_for_worker(order, bulk_items)
    earnings = calculate_worker_earnings_from_order(order_income, worker)

    if earnings <= 0:
        return Decimal("0")

    await LedgerService.credit_worker_balance(
        session,
        worker_id=worker.id,
        amount=earnings,
        description=f"Worker payout for order #{order.id}",
        related_entity_type="order",
        related_entity_id=order.id,
        idempotency_key=LedgerService.build_idempotency_key("worker-order", order.id, worker.id),
    )
    logger.info(f"Worker {worker_id} credited ${earnings} (order #{order.id}, order_income=${order_income})")
    return earnings
