import unittest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from shared.database.models import Base, Worker, WorkerViolation
from shared.utils.chat_filter import check_violations, filter_and_log, filter_message, is_message_blocked


class ChatFilterTests(unittest.TestCase):
    def test_filter_message_masks_multiple_contact_types(self) -> None:
        raw = "Write to me @sellername or test@example.com and whatsapp: +15551234567"
        filtered = filter_message(raw)

        self.assertNotIn("@sellername", filtered)
        self.assertNotIn("test@example.com", filtered)
        self.assertNotIn("+15551234567", filtered)
        self.assertIn("[КОНТАКТ СКРЫТ]", filtered)
        self.assertIn("[EMAIL СКРЫТ]", filtered)

    def test_is_message_blocked_for_contact_only_payload(self) -> None:
        self.assertTrue(is_message_blocked("@onlycontact"))
        self.assertTrue(is_message_blocked("https://t.me/example"))
        self.assertFalse(is_message_blocked("Result is ready @contact"))

    def test_check_violations_detects_new_v24_patterns(self) -> None:
        violations = check_violations("discord user test#1234 and email me at qa@example.com via signal: abc")
        self.assertIn("discord", violations)
        self.assertIn("email", violations)
        self.assertIn("whatsapp", violations)


class ChatFilterDbTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_filter_and_log_creates_violation_and_updates_worker_counter(self) -> None:
        async with self.session_maker() as session:
            worker = Worker(
                telegram_id=991001,
                username="worker_filter",
                categories=["lookup"],
                services=["ssn"],
            )
            session.add(worker)
            await session.commit()
            await session.refresh(worker)

            filtered, violated = await filter_and_log(
                text="Contact me at test@example.com or @worker_filter",
                worker_id=worker.id,
                order_id=None,
                session=session,
            )
            await session.commit()
            await session.refresh(worker)

            self.assertTrue(violated)
            self.assertIn("[EMAIL СКРЫТ]", filtered)
            self.assertGreaterEqual(worker.violation_count, 1)

            rows = (await session.execute(select(WorkerViolation))).scalars().all()
            self.assertEqual(len(rows), 1)
            self.assertIn("email", rows[0].violation_type)
