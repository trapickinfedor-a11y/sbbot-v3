import unittest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from shared.database.models import AuditLog, Base
from shared.services.audit_event_service import AuditEventService


class AuditEventServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_log_writes_universal_audit_row(self) -> None:
        async with self.session_maker() as session:
            event = await AuditEventService.log(
                session,
                event_type="coupon_applied",
                source="mirror_bot",
                actor_type="buyer",
                actor_id=123,
                target_type="order",
                target_id=987,
                status="applied",
                payload={"coupon_code": "SPRING10"},
                commit=True,
            )

            self.assertIsNotNone(event.id)
            row = await session.scalar(select(AuditLog).where(AuditLog.id == event.id))
            self.assertIsNotNone(row)
            self.assertEqual(row.source, "mirror_bot")
            self.assertEqual(row.event_type, "coupon_applied")
            self.assertEqual(row.actor_id, 123)
            self.assertEqual(row.target_id, 987)
