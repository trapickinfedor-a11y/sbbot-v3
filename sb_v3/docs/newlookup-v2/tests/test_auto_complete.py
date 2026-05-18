import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from shared.database.models import (
    AuditLog,
    Base,
    EscrowRelease,
    Marketer,
    MarketerActivityLog,
    Seller,
    SellerBank,
    SellerOrder,
)
from shared.tasks.auto_complete import _release_escrow_for_order


class AutoCompleteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_release_escrow_settles_seller_and_pays_marketer_once(self) -> None:
        async with self.session_maker() as session:
            seller = Seller(
                telegram_id=555001,
                username="seller_auto",
                display_name="Seller Auto",
                pending_balance=Decimal("20.00"),
                withdrawable_balance=Decimal("0.00"),
                deposit_balance=Decimal("0.00"),
                total_earned=Decimal("0.00"),
            )
            marketer = Marketer(
                telegram_id=777001,
                username="marketer_auto",
                display_name="Marketer Auto",
                promo_code="AUTO100",
                balance=Decimal("0.00"),
                total_earned=Decimal("0.00"),
            )
            session.add_all([seller, marketer])
            await session.commit()
            await session.refresh(seller)
            await session.refresh(marketer)

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
            )
            session.add(bank)
            await session.commit()
            await session.refresh(bank)

            order = SellerOrder(
                seller_id=seller.id,
                seller_bank_id=bank.id,
                buyer_user_id=999001,
                status="completed",
                price_for_buyer=Decimal("30.00"),
                price_for_seller=Decimal("20.00"),
                marketer_id=marketer.id,
                marketer_commission_amount=Decimal("3.00"),
                marketer_commission_paid=False,
                escrow_released=False,
                auto_complete_at=datetime.utcnow() - timedelta(hours=1),
                pending_credited_at=datetime.utcnow() - timedelta(hours=2),
            )
            session.add(order)
            await session.commit()
            await session.refresh(order)

            await _release_escrow_for_order(session, order)
            await session.commit()

            await session.refresh(seller)
            await session.refresh(marketer)
            await session.refresh(order)

            self.assertTrue(order.escrow_released)
            self.assertTrue(order.marketer_commission_paid)
            self.assertIsNotNone(order.settled_at)
            self.assertEqual(Decimal(str(seller.pending_balance)), Decimal("0.00"))
            self.assertEqual(Decimal(str(seller.withdrawable_balance)), Decimal("20.00"))
            self.assertEqual(Decimal(str(seller.deposit_balance)), Decimal("0.00"))
            self.assertEqual(Decimal(str(seller.total_earned)), Decimal("20.00"))
            self.assertEqual(Decimal(str(marketer.balance)), Decimal("3.00"))
            self.assertEqual(Decimal(str(marketer.total_earned)), Decimal("3.00"))

            audit_rows = (await session.execute(select(AuditLog).order_by(AuditLog.id.asc()))).scalars().all()
            self.assertEqual(len(audit_rows), 2)
            self.assertEqual(audit_rows[0].event_type, "seller_order_escrow_released")
            self.assertEqual(audit_rows[1].event_type, "marketer_commission_paid")
            release_rows = (await session.execute(select(EscrowRelease))).scalars().all()
            self.assertEqual(len(release_rows), 1)
            self.assertEqual(release_rows[0].seller_order_id, order.id)
            self.assertEqual(Decimal(str(release_rows[0].amount)), Decimal("20.00"))

            marketer_logs = (await session.execute(select(MarketerActivityLog))).scalars().all()
            self.assertEqual(len(marketer_logs), 1)
            self.assertEqual(marketer_logs[0].action, "earning")
            self.assertEqual(Decimal(str(marketer_logs[0].amount)), Decimal("3.00"))

    async def test_release_escrow_is_idempotent_on_second_run(self) -> None:
        async with self.session_maker() as session:
            seller = Seller(
                telegram_id=555002,
                username="seller_auto_2",
                display_name="Seller Auto 2",
                pending_balance=Decimal("10.00"),
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
                seller_price=Decimal("10.00"),
                buyer_price=Decimal("15.00"),
                stock_count=1,
                is_in_stock=True,
                is_active=True,
            )
            session.add(bank)
            await session.commit()
            await session.refresh(bank)

            order = SellerOrder(
                seller_id=seller.id,
                seller_bank_id=bank.id,
                buyer_user_id=999002,
                status="completed",
                price_for_buyer=Decimal("15.00"),
                price_for_seller=Decimal("10.00"),
                escrow_released=False,
                auto_complete_at=datetime.utcnow() - timedelta(hours=1),
                pending_credited_at=datetime.utcnow() - timedelta(hours=2),
            )
            session.add(order)
            await session.commit()
            await session.refresh(order)

            await _release_escrow_for_order(session, order)
            await session.commit()
            first_totals = (
                Decimal(str(seller.pending_balance)),
                Decimal(str(seller.withdrawable_balance)),
                Decimal(str(seller.deposit_balance)),
                Decimal(str(seller.total_earned)),
            )

            await _release_escrow_for_order(session, order)
            await session.commit()

            await session.refresh(seller)
            await session.refresh(order)

            second_totals = (
                Decimal(str(seller.pending_balance)),
                Decimal(str(seller.withdrawable_balance)),
                Decimal(str(seller.deposit_balance)),
                Decimal(str(seller.total_earned)),
            )
            self.assertEqual(first_totals, second_totals)
            self.assertTrue(order.escrow_released)

            audit_rows = (await session.execute(select(AuditLog))).scalars().all()
            self.assertEqual(len(audit_rows), 1)
            release_rows = (await session.execute(select(EscrowRelease))).scalars().all()
            self.assertEqual(len(release_rows), 1)
