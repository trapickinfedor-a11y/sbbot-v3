import unittest
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from shared.database.models import Base, Transaction, User, TRANSACTION_STATUS_COMPLETED
from support_bot.services.balance_service import BalanceService


class BalanceServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_refund_order_commits_balance_and_transaction(self) -> None:
        async with self.session_maker() as session:
            user = User(
                user_id=900001,
                username="buyer_refund",
                mirror_bot_id=1,
                balance=Decimal("10.00"),
                referral_link="buyer-refund-link",
            )
            session.add(user)
            await session.commit()

            result = await BalanceService.refund_order(
                session,
                user_id=user.user_id,
                amount=Decimal("5.50"),
                order_id=101,
                commit=True,
            )

            self.assertTrue(result)
            await session.refresh(user)
            self.assertEqual(Decimal(str(user.balance)), Decimal("15.50"))

            transactions = (await session.execute(select(Transaction).order_by(Transaction.id.asc()))).scalars().all()
            self.assertEqual(len(transactions), 2)
            self.assertEqual(transactions[-1].type, "refund")
            self.assertEqual(Decimal(str(transactions[-1].amount)), Decimal("5.50"))
            self.assertEqual(transactions[-1].status, TRANSACTION_STATUS_COMPLETED)

    async def test_refund_order_flushes_without_commit_when_requested(self) -> None:
        async with self.session_maker() as session:
            user = User(
                user_id=900002,
                username="buyer_refund_2",
                mirror_bot_id=1,
                balance=Decimal("20.00"),
                referral_link="buyer-refund-link-2",
            )
            session.add(user)
            await session.commit()

            result = await BalanceService.refund_order(
                session,
                user_id=user.user_id,
                amount=Decimal("4.00"),
                order_id=202,
                commit=False,
            )

            self.assertTrue(result)
            self.assertEqual(Decimal(str(user.balance)), Decimal("24.00"))
            pending_transactions = (await session.execute(select(Transaction))).scalars().all()
            self.assertEqual(len(pending_transactions), 2)

            await session.rollback()
        async with self.session_maker() as verify_session:
            refreshed_user = await verify_session.scalar(select(User).where(User.user_id == 900002))
            self.assertEqual(Decimal(str(refreshed_user.balance)), Decimal("20.00"))
