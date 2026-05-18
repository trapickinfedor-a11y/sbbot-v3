from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import Order, WorkerOrder


STATUS_MAP = {
    "pending": "new",
    "processing": "in_progress",
    "completed": "completed",
    "cancelled": "rejected",
}


class WorkerOrderService:
    """Keep additive worker_orders rows synchronized with legacy orders."""

    @staticmethod
    async def ensure_from_order(session: AsyncSession, order: Order) -> WorkerOrder:
        row = await session.scalar(select(WorkerOrder).where(WorkerOrder.order_id == order.id))
        if row is None:
            row = WorkerOrder(
                order_id=order.id,
                customer_id=order.user_id,
                category_slug=(order.category or "").strip().lower(),
                input_data=order.input_data or {},
            )
            session.add(row)
        row.worker_id = order.worker_id
        row.customer_id = order.user_id
        row.category_slug = (order.category or "").strip().lower()
        row.input_data = order.input_data or {}
        row.status = STATUS_MAP.get(order.status, order.status or "new")
        row.last_reminder_at = getattr(order, "last_worker_reminder_at", None)
        row.result_data = order.result_data
        row.files = order.files
        row.taken_at = order.taken_at
        row.completed_at = order.completed_at
        await session.flush()
        return row

    @staticmethod
    async def ensure_by_order_id(session: AsyncSession, order_id: int) -> WorkerOrder | None:
        order = await session.scalar(select(Order).where(Order.id == order_id))
        if not order:
            return None
        return await WorkerOrderService.ensure_from_order(session, order)
