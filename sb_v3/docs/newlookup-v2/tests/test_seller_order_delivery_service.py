import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from shared.database.models import Base, Seller, SellerBank, SellerOrder, Transaction, TRANSACTION_STATUS_ON_HOLD
from shared.services.seller_finance_service import SellerFinanceService
from shared.services.seller_order_delivery_service import (
    confirm_seller_order,
    mark_seller_order_completed,
)


class SellerOrderDeliveryServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_mark_completed_sets_timers_and_credits_pending_once(self) -> None:
        async with self.session_maker() as session:
            seller = Seller(
                telegram_id=880001,
                username="seller_test",
                display_name="Seller Test",
                pending_balance=Decimal("0.00"),
                withdrawable_balance=Decimal("0.00"),
                deposit_balance=Decimal("0.00"),
                total_orders=0,
            )
            session.add(seller)
            await session.commit()
            await session.refresh(seller)

            bank = SellerBank(
                seller_id=seller.id,
                bank_name="Chase",
                bank_code="chase",
                category="personal",
                seller_price=Decimal("20.00"),
                buyer_price=Decimal("30.00"),
                stock_count=1,
                is_in_stock=True,
                is_active=True,
                has_chat=True,
            )
            session.add(bank)
            await session.commit()
            await session.refresh(bank)

            order = SellerOrder(
                seller_id=seller.id,
                seller_bank_id=bank.id,
                buyer_user_id=700001,
                status="approved",
                price_for_buyer=Decimal("30.00"),
                price_for_seller=Decimal("20.00"),
                quantity=1,
            )
            session.add(order)
            await session.commit()
            await session.refresh(order)

            await mark_seller_order_completed(session, order, seller, result_text="clean result")
            await session.refresh(order)
            await session.refresh(seller)

            self.assertEqual(order.status, "completed")
            self.assertIsNotNone(order.completed_at)
            self.assertIsNotNone(order.check_expires_at)
            self.assertIsNotNone(order.auto_complete_at)
            self.assertIsNotNone(order.dispute_deadline_at)
            self.assertEqual(order.result_data, {"text": "clean result"})
            self.assertEqual(Decimal(str(SellerFinanceService.pending_balance(seller))), Decimal("20.00"))
            self.assertEqual(seller.total_orders, 1)
            hold_tx = await session.scalar(
                select(Transaction).where(Transaction.related_entity_type == "seller_order", Transaction.related_entity_id == order.id)
            )
            self.assertIsNotNone(hold_tx)
            self.assertEqual(hold_tx.status, TRANSACTION_STATUS_ON_HOLD)

            await mark_seller_order_completed(session, order, seller, result_text="updated result")
            await session.refresh(order)
            await session.refresh(seller)

            self.assertEqual(order.result_data, {"text": "updated result"})
            self.assertEqual(Decimal(str(SellerFinanceService.pending_balance(seller))), Decimal("20.00"))
            self.assertEqual(seller.total_orders, 1)

    async def test_confirm_order_settles_pending_only_once(self) -> None:
        async with self.session_maker() as session:
            seller = Seller(
                telegram_id=880002,
                username="seller_test_2",
                display_name="Seller Test 2",
                pending_balance=Decimal("20.00"),
                withdrawable_balance=Decimal("0.00"),
                deposit_balance=Decimal("0.00"),
                total_earned=Decimal("0.00"),
            )
            session.add(seller)
            await session.commit()
            await session.refresh(seller)

            bank = SellerBank(
                seller_id=seller.id,
                bank_name="BoA",
                bank_code="boa",
                category="personal",
                seller_price=Decimal("20.00"),
                buyer_price=Decimal("25.00"),
                stock_count=1,
                is_in_stock=True,
                is_active=True,
                has_chat=False,
            )
            session.add(bank)
            await session.commit()
            await session.refresh(bank)

            order = SellerOrder(
                seller_id=seller.id,
                seller_bank_id=bank.id,
                buyer_user_id=700002,
                status="completed",
                price_for_buyer=Decimal("25.00"),
                price_for_seller=Decimal("20.00"),
                quantity=1,
                pending_credited_at=datetime.utcnow() - timedelta(hours=1),
                check_expires_at=datetime.utcnow() + timedelta(minutes=15),
            )
            session.add(order)
            await session.commit()
            await session.refresh(order)

            first = await confirm_seller_order(session, order)
            await session.refresh(order)
            await session.refresh(seller)

            self.assertTrue(first)
            self.assertIsNotNone(order.check_confirmed_at)
            self.assertIsNotNone(order.settled_at)
            self.assertEqual(Decimal(str(SellerFinanceService.pending_balance(seller))), Decimal("0.00"))
            self.assertEqual(Decimal(str(SellerFinanceService.withdrawable_balance(seller))), Decimal("20.00"))
            self.assertEqual(Decimal(str(seller.total_earned)), Decimal("20.00"))

            second = await confirm_seller_order(session, order)
            await session.refresh(order)
            await session.refresh(seller)

            self.assertFalse(second)
            self.assertEqual(Decimal(str(SellerFinanceService.withdrawable_balance(seller))), Decimal("20.00"))
