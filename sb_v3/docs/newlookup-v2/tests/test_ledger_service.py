import unittest
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from shared.database.models import Base, BotOwner, Seller, Transaction, Worker
from shared.services.ledger_service import LedgerService
from shared.services.seller_finance_service import SellerFinanceService


class LedgerServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_seller_task_withdrawal_reserve_finalize_and_release_are_namespaced(self) -> None:
        async with self.session_maker() as session:
            seller = Seller(
                telegram_id=990001,
                username="seller_ledger",
                display_name="Seller Ledger",
                withdrawable_balance=Decimal("0.00"),
                deposit_balance=Decimal("0.00"),
                pending_balance=Decimal("0.00"),
            )
            session.add(seller)
            await session.commit()
            await session.refresh(seller)

            await LedgerService.create_seller_hold(
                session,
                seller_id=seller.id,
                amount=Decimal("100.00"),
                order_id=1011,
                effective_at=None,
                description="Initial seller earnings",
            )
            await LedgerService.settle_seller_hold(
                session,
                seller_id=seller.id,
                order_id=1011,
            )
            await session.refresh(seller)

            reserved = await LedgerService.reserve_seller_withdrawal(
                session,
                seller=seller,
                amount=Decimal("30.00"),
                withdrawal_id=11,
                related_entity_type="seller_withdrawal_task",
                key_prefix="seller-task-withdrawal",
                description="Seller withdrawal task #11",
            )
            self.assertTrue(reserved)
            self.assertEqual(Decimal(str(SellerFinanceService.withdrawable_balance(seller))), Decimal("70.00"))

            reserved_again = await LedgerService.reserve_seller_withdrawal(
                session,
                seller=seller,
                amount=Decimal("30.00"),
                withdrawal_id=11,
                related_entity_type="seller_withdrawal_task",
                key_prefix="seller-task-withdrawal",
                description="Seller withdrawal task #11",
            )
            self.assertTrue(reserved_again)
            self.assertEqual(Decimal(str(SellerFinanceService.withdrawable_balance(seller))), Decimal("70.00"))

            await LedgerService.finalize_seller_withdrawal(
                session,
                seller=seller,
                amount=Decimal("30.00"),
                withdrawal_id=11,
                key_prefix="seller-task-withdrawal",
            )
            await session.commit()
            await session.refresh(seller)

            tx = await session.scalar(
                select(Transaction).where(Transaction.idempotency_key == "seller-task-withdrawal:11")
            )
            self.assertIsNotNone(tx)
            self.assertEqual(tx.status, "completed")
            self.assertEqual(Decimal(str(tx.amount)), Decimal("-30.00"))

    async def test_worker_task_withdrawal_release_returns_balance(self) -> None:
        async with self.session_maker() as session:
            worker = Worker(
                telegram_id=990002,
                username="worker_ledger",
                categories=["lookup"],
                balance=Decimal("0.00"),
                total_withdrawn=Decimal("0.00"),
            )
            session.add(worker)
            await session.commit()
            await session.refresh(worker)

            await LedgerService.credit_worker_balance(
                session,
                worker_id=worker.id,
                amount=Decimal("45.00"),
                description="Initial worker earnings",
            )
            await session.refresh(worker)

            reserved = await LedgerService.reserve_worker_withdrawal(
                session,
                worker=worker,
                amount=Decimal("15.00"),
                withdrawal_id=22,
                related_entity_type="worker_withdrawal_task",
                key_prefix="worker-task-withdrawal",
                description="Worker withdrawal task #22",
            )
            self.assertTrue(reserved)
            self.assertEqual(Decimal(str(worker.balance)), Decimal("30.00"))

            await LedgerService.release_worker_withdrawal_reservation(
                session,
                worker=worker,
                amount=Decimal("15.00"),
                withdrawal_id=22,
                key_prefix="worker-task-withdrawal",
            )
            await session.commit()
            await session.refresh(worker)

            self.assertEqual(Decimal(str(worker.balance)), Decimal("45.00"))
            tx = await session.scalar(
                select(Transaction).where(Transaction.idempotency_key == "worker-task-withdrawal:22")
            )
            self.assertIsNotNone(tx)
            self.assertEqual(tx.status, "failed")

    async def test_worker_withdrawal_finalize_is_idempotent_on_repeat(self) -> None:
        async with self.session_maker() as session:
            worker = Worker(
                telegram_id=990003,
                username="worker_finalize",
                categories=["lookup"],
                balance=Decimal("0.00"),
                total_withdrawn=Decimal("0.00"),
            )
            session.add(worker)
            await session.commit()
            await session.refresh(worker)

            await LedgerService.credit_worker_balance(
                session,
                worker_id=worker.id,
                amount=Decimal("20.00"),
                description="Initial worker earnings",
            )
            await session.refresh(worker)

            reserved = await LedgerService.reserve_worker_withdrawal(
                session,
                worker=worker,
                amount=Decimal("5.00"),
                withdrawal_id=33,
                related_entity_type="worker_withdrawal_task",
                key_prefix="worker-task-withdrawal",
                description="Worker withdrawal task #33",
            )
            self.assertTrue(reserved)
            await LedgerService.finalize_worker_withdrawal(
                session,
                worker=worker,
                amount=Decimal("5.00"),
                withdrawal_id=33,
                key_prefix="worker-task-withdrawal",
            )
            await LedgerService.finalize_worker_withdrawal(
                session,
                worker=worker,
                amount=Decimal("5.00"),
                withdrawal_id=33,
                key_prefix="worker-task-withdrawal",
            )
            await session.commit()
            await session.refresh(worker)

            self.assertEqual(Decimal(str(worker.balance)), Decimal("15.00"))
            self.assertEqual(Decimal(str(worker.total_withdrawn)), Decimal("5.00"))

    async def test_owner_withdrawal_uses_ledger_projection_when_balance_field_is_stale(self) -> None:
        async with self.session_maker() as session:
            owner = BotOwner(owner_user_id=990004, balance=Decimal("0.00"), total_withdrawn=Decimal("0.00"))
            session.add(owner)
            await session.commit()

            await LedgerService.credit_owner_balance(
                session,
                owner_user_id=owner.owner_user_id,
                amount=Decimal("20.00"),
                description="Owner income",
            )
            await session.commit()
            await session.refresh(owner)

            owner.balance = Decimal("0.00")
            await session.flush()

            reserved = await LedgerService.reserve_owner_withdrawal(
                session,
                owner=owner,
                amount=Decimal("8.00"),
                withdrawal_id=44,
            )
            self.assertTrue(reserved)
            self.assertEqual(Decimal(str(owner.balance)), Decimal("12.00"))

    async def test_seller_withdrawal_does_not_use_legacy_deposit_balance_as_source_of_truth(self) -> None:
        async with self.session_maker() as session:
            seller = Seller(
                telegram_id=990005,
                username="seller_projection",
                display_name="Seller Projection",
                withdrawable_balance=Decimal("0.00"),
                deposit_balance=Decimal("100.00"),
                pending_balance=Decimal("0.00"),
            )
            session.add(seller)
            await session.commit()
            await session.refresh(seller)

            reserved = await LedgerService.reserve_seller_withdrawal(
                session,
                seller=seller,
                amount=Decimal("10.00"),
                withdrawal_id=55,
            )
            self.assertFalse(reserved)
            self.assertEqual(Decimal(str(SellerFinanceService.withdrawable_balance(seller))), Decimal("0.00"))
