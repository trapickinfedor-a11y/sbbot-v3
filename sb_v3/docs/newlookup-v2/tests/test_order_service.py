import unittest
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from mirror_bot.services.order_service import OrderService
from shared.database.models import Base, Coupon, CouponRedemption, Referral, Transaction, User, WorkerOrder, TRANSACTION_STATUS_COMPLETED


class OrderServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_charge_and_refund_balance_helpers(self) -> None:
        async with self.session_maker() as session:
            user = User(
                user_id=810001,
                username="buyer_order_service",
                mirror_bot_id=1,
                balance=Decimal("50.00"),
                referral_link="buyer-order-service-link",
            )
            session.add(user)
            await session.commit()

            charged = await OrderService.charge_balance(
                session,
                user_id=user.user_id,
                amount=Decimal("15.00"),
                description="Manual charge",
                commit=True,
            )
            self.assertTrue(charged)
            await session.refresh(user)
            self.assertEqual(Decimal(str(user.balance)), Decimal("35.00"))

            refunded = await OrderService.refund_balance(
                session,
                user_id=user.user_id,
                amount=Decimal("5.00"),
                description="Manual refund",
                commit=True,
            )
            self.assertTrue(refunded)
            await session.refresh(user)
            self.assertEqual(Decimal(str(user.balance)), Decimal("40.00"))

            transactions = (await session.execute(select(Transaction).order_by(Transaction.id.asc()))).scalars().all()
            self.assertEqual(len(transactions), 3)
            self.assertEqual(transactions[-2].type, "purchase")
            self.assertEqual(transactions[-2].status, TRANSACTION_STATUS_COMPLETED)
            self.assertEqual(Decimal(str(transactions[-2].amount)), Decimal("-15.00"))
            self.assertEqual(transactions[-1].type, "refund")
            self.assertEqual(transactions[-1].status, TRANSACTION_STATUS_COMPLETED)
            self.assertEqual(Decimal(str(transactions[-1].amount)), Decimal("5.00"))

    async def test_credit_referral_commission_updates_referrer_and_referral_row(self) -> None:
        async with self.session_maker() as session:
            buyer = User(
                user_id=810002,
                username="buyer_ref",
                mirror_bot_id=1,
                balance=Decimal("0.00"),
                referral_link="buyer-ref-link",
                referrer_id=810003,
            )
            referrer = User(
                user_id=810003,
                username="referrer_ref",
                mirror_bot_id=1,
                balance=Decimal("1.00"),
                referral_link="referrer-ref-link",
            )
            referral = Referral(referrer_id=referrer.user_id, referred_id=buyer.user_id)
            session.add_all([buyer, referrer, referral])
            await session.commit()

            await OrderService._credit_referral_commission(
                session,
                user_id=buyer.user_id,
                order_price=Decimal("25.00"),
                order_id=909,
                commit=True,
            )

            await session.refresh(referrer)
            await session.refresh(referral)

            self.assertEqual(Decimal(str(referrer.balance)), Decimal("2.00"))
            self.assertEqual(Decimal(str(referral.earned_total)), Decimal("1.00"))

            transactions = (await session.execute(select(Transaction))).scalars().all()
            self.assertEqual(len(transactions), 2)
            self.assertEqual(transactions[-1].type, "referral_commission")

    async def test_create_order_keeps_coupon_and_referral_side_effects_consistent(self) -> None:
        async with self.session_maker() as session:
            referrer = User(
                user_id=810010,
                username="referrer_flow",
                mirror_bot_id=1,
                balance=Decimal("0.00"),
                referral_link="referrer-flow-link",
            )
            buyer = User(
                user_id=810011,
                username="buyer_flow",
                mirror_bot_id=1,
                balance=Decimal("0.00"),
                referrer_id=referrer.user_id,
                active_coupon_code="FLOW10",
                referral_link="buyer-flow-link",
            )
            coupon = Coupon(
                code="FLOW10",
                discount_type="fixed",
                discount_value=Decimal("10.00"),
                is_active=True,
            )
            referral = Referral(referrer_id=referrer.user_id, referred_id=buyer.user_id)
            session.add_all([referrer, buyer, coupon, referral])
            await session.commit()

            order = await OrderService.create_order(
                session,
                user_id=buyer.user_id,
                mirror_bot_id=1,
                category="lookup",
                service_name="ssn_lookup",
                input_data={"ssn": "123-45-6789"},
                price=Decimal("50.00"),
                bulk_items=[{"ssn": "1"}, {"ssn": "2"}],
                notify_workers=False,
                notify_channel=False,
            )

            await session.refresh(buyer)
            await session.refresh(referrer)
            await session.refresh(referral)

            self.assertEqual(order.bulk_count, 2)
            self.assertEqual(Decimal(str(order.price)), Decimal("40.00"))
            self.assertEqual(order.coupon_code, "FLOW10")
            self.assertEqual(Decimal(str(order.discount_amount)), Decimal("10.00"))
            self.assertEqual(Decimal(str(buyer.balance)), Decimal("10.00"))
            self.assertEqual(Decimal(str(referrer.balance)), Decimal("1.60"))
            self.assertEqual(Decimal(str(referral.earned_total)), Decimal("1.60"))

            redemptions = (await session.execute(select(CouponRedemption))).scalars().all()
            self.assertEqual(len(redemptions), 1)
            self.assertEqual(redemptions[0].coupon_id, coupon.id)

            worker_rows = (await session.execute(select(WorkerOrder).where(WorkerOrder.order_id == order.id))).scalars().all()
            self.assertEqual(len(worker_rows), 1)

            tx_rows = (await session.execute(select(Transaction).order_by(Transaction.id.asc()))).scalars().all()
            self.assertEqual(len(tx_rows), 2)
            self.assertEqual(tx_rows[0].type, "refund")
            self.assertEqual(tx_rows[1].type, "referral_commission")
