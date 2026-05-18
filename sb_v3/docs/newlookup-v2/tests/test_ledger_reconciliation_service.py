import unittest
from decimal import Decimal

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from shared.database.models import Base, BotOwner, Marketer, Seller, User, Worker
from shared.services.ledger_reconciliation_service import LedgerReconciliationService
from shared.services.ledger_service import LedgerService


class LedgerReconciliationServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_reconciliation_passes_for_consistent_balances(self) -> None:
        async with self.session_maker() as session:
            user = User(user_id=101, username="buyer", mirror_bot_id=1, balance=Decimal("0.00"), referral_link="u-101")
            seller = Seller(
                telegram_id=202,
                username="seller",
                display_name="Seller",
                is_approved=True,
                is_active=True,
                access_status="active",
            )
            worker = Worker(telegram_id=303, username="worker", categories=["lookup"], balance=Decimal("0.00"))
            marketer = Marketer(telegram_id=404, username="marketer", display_name="Marketer", promo_code="MRK404")
            owner = BotOwner(owner_user_id=505, balance=Decimal("0.00"))
            session.add_all([user, seller, worker, marketer, owner])
            await session.commit()
            await session.refresh(seller)
            await session.refresh(worker)
            await session.refresh(marketer)
            await session.refresh(owner)

            await LedgerService.credit_user_balance(
                session,
                user_id=user.user_id,
                amount=Decimal("100.00"),
                tx_type="topup",
                description="Topup",
            )
            await LedgerService.debit_user_balance(
                session,
                user_id=user.user_id,
                amount=Decimal("25.00"),
                tx_type="purchase",
                description="Purchase",
            )

            await LedgerService.create_seller_hold(
                session,
                seller_id=seller.id,
                amount=Decimal("20.00"),
                order_id=1,
                effective_at=None,
                description="Hold one",
            )
            await LedgerService.create_seller_hold(
                session,
                seller_id=seller.id,
                amount=Decimal("10.00"),
                order_id=2,
                effective_at=None,
                description="Hold two",
            )
            await LedgerService.settle_seller_hold(session, seller_id=seller.id, order_id=2)

            await LedgerService.credit_worker_balance(
                session,
                worker_id=worker.id,
                amount=Decimal("7.00"),
                description="Worker payout",
            )
            await LedgerService.reserve_worker_withdrawal(
                session,
                worker=worker,
                amount=Decimal("2.00"),
                withdrawal_id=10,
            )

            await LedgerService.credit_marketer_balance(
                session,
                marketer_id=marketer.id,
                amount=Decimal("9.00"),
                description="Commission",
            )
            await LedgerService.reserve_marketer_withdrawal(
                session,
                marketer=marketer,
                amount=Decimal("4.00"),
                withdrawal_id=11,
            )
            await LedgerService.finalize_marketer_withdrawal(
                session,
                marketer=marketer,
                amount=Decimal("4.00"),
                withdrawal_id=11,
            )

            await LedgerService.credit_owner_balance(
                session,
                owner_user_id=owner.owner_user_id,
                amount=Decimal("8.00"),
                description="Owner income",
            )
            await LedgerService.reserve_owner_withdrawal(
                session,
                owner=owner,
                amount=Decimal("3.00"),
                withdrawal_id=12,
            )

            await session.commit()

            result = await LedgerReconciliationService.run_full_reconciliation(session, emit_alerts=False)
            self.assertTrue(result["ok"])
            self.assertEqual(result["issue_count"], 0)

    async def test_reconciliation_detects_balance_drift(self) -> None:
        async with self.session_maker() as session:
            user = User(user_id=111, username="drift_user", mirror_bot_id=1, balance=Decimal("0.00"), referral_link="u-111")
            session.add(user)
            await session.commit()

            await LedgerService.credit_user_balance(
                session,
                user_id=user.user_id,
                amount=Decimal("10.00"),
                tx_type="topup",
                description="Topup",
            )
            await session.commit()

            user.balance = Decimal("8.00")
            await session.commit()

            result = await LedgerReconciliationService.run_full_reconciliation(session, emit_alerts=False)
            self.assertFalse(result["ok"])
            self.assertEqual(result["issue_count"], 1)
            self.assertEqual(result["issues"][0]["account_type"], "user")
            self.assertEqual(result["issues"][0]["field"], "balance")
