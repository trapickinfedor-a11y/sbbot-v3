from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.task_models import WorkerReminderTask


class WorkerReminderTaskService:
    """Durable reminder task bookkeeping in the tasks DB."""

    @staticmethod
    async def schedule(
        session: AsyncSession,
        *,
        order_id: int,
        worker_order_id: Optional[int],
        worker_id: Optional[int],
        worker_telegram_id: Optional[int],
        delay_hours: float,
        payload_json: Optional[dict] = None,
    ) -> WorkerReminderTask:
        row = await session.scalar(
            select(WorkerReminderTask).where(
                WorkerReminderTask.order_id == order_id,
                WorkerReminderTask.status == "pending",
                WorkerReminderTask.is_active == True,
            )
        )
        scheduled_for = datetime.now(timezone.utc) + timedelta(hours=float(delay_hours))
        if row is None:
            row = WorkerReminderTask(
                order_id=order_id,
                worker_order_id=worker_order_id,
                worker_id=worker_id,
                worker_telegram_id=worker_telegram_id,
                scheduled_for=scheduled_for,
                payload_json=payload_json or {},
            )
            session.add(row)
        else:
            row.worker_order_id = worker_order_id
            row.worker_id = worker_id
            row.worker_telegram_id = worker_telegram_id
            row.scheduled_for = scheduled_for
            row.payload_json = payload_json or row.payload_json
            row.status = "pending"
            row.is_active = True
            row.last_error = None
        await session.commit()
        await session.refresh(row)
        return row

    @staticmethod
    async def cancel_for_order(session: AsyncSession, order_id: int) -> None:
        rows = (
            await session.execute(
                select(WorkerReminderTask).where(
                    WorkerReminderTask.order_id == order_id,
                    WorkerReminderTask.is_active == True,
                    WorkerReminderTask.status == "pending",
                )
            )
        ).scalars().all()
        for row in rows:
            row.status = "cancelled"
            row.is_active = False
        await session.commit()
