import unittest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from shared.database.task_models import TaskBase, WorkerReminderTask
from shared.services.worker_reminder_task_service import WorkerReminderTaskService


class WorkerReminderTaskServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(TaskBase.metadata.create_all)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_schedule_updates_existing_pending_task(self) -> None:
        async with self.session_maker() as session:
            first = await WorkerReminderTaskService.schedule(
                session,
                order_id=11,
                worker_order_id=22,
                worker_id=33,
                worker_telegram_id=44,
                delay_hours=2,
                payload_json={"source": "take_order"},
            )
            second = await WorkerReminderTaskService.schedule(
                session,
                order_id=11,
                worker_order_id=22,
                worker_id=33,
                worker_telegram_id=55,
                delay_hours=4,
                payload_json={"source": "snooze"},
            )

            self.assertEqual(first.id, second.id)
            rows = (await session.execute(select(WorkerReminderTask))).scalars().all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].worker_telegram_id, 55)
            self.assertEqual(rows[0].payload_json["source"], "snooze")

    async def test_cancel_for_order_marks_tasks_inactive(self) -> None:
        async with self.session_maker() as session:
            await WorkerReminderTaskService.schedule(
                session,
                order_id=99,
                worker_order_id=199,
                worker_id=299,
                worker_telegram_id=399,
                delay_hours=1,
            )
            await WorkerReminderTaskService.cancel_for_order(session, 99)
            row = await session.scalar(select(WorkerReminderTask).where(WorkerReminderTask.order_id == 99))
            self.assertEqual(row.status, "cancelled")
            self.assertFalse(row.is_active)
