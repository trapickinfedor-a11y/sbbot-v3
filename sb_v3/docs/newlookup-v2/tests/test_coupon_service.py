import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from shared.database.models import Base, Coupon, CouponRedemption, Order, User, UserCoupon
from shared.services.coupon_service import CouponService


class CouponServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def test_calculate_discount_and_record_redemption(self) -> None:
        async with self.session_maker() as session:
            user = User(
                user_id=10101,
                username="buyer",
                mirror_bot_id=1,
                referral_link="buyer-link",
            )
            coupon = Coupon(
                code="SPRING10",
                discount_type="percent",
                discount_value=Decimal("10.00"),
                is_active=True,
                starts_at=datetime.utcnow() - timedelta(days=1),
                ends_at=datetime.utcnow() + timedelta(days=1),
                allowed_categories=["lookup"],
                allowed_services=["ssn_lookup"],
            )
            session.add_all([user, coupon])
            await session.commit()

            assigned = await CouponService.assign_coupon_to_user(session, user, "spring10")
            self.assertEqual(assigned.code, "SPRING10")
            activation_rows = (await session.execute(select(UserCoupon))).scalars().all()
            self.assertEqual(len(activation_rows), 1)
            self.assertFalse(activation_rows[0].is_used)

            pricing = await CouponService.calculate_discount(
                session,
                user_id=user.user_id,
                category="lookup",
                service_name="ssn_lookup",
                amount=Decimal("50.00"),
            )
            self.assertTrue(pricing.applied)
            self.assertEqual(pricing.discount_amount, Decimal("5.00"))
            self.assertEqual(pricing.final_amount, Decimal("45.00"))

            order = Order(
                user_id=user.user_id,
                mirror_bot_id=user.mirror_bot_id,
                category="lookup",
                service_name="ssn_lookup",
                input_data={"q": "x"},
                price=pricing.final_amount,
                original_price=pricing.original_amount,
                coupon_code=pricing.code,
                discount_amount=pricing.discount_amount,
            )
            session.add(order)
            await session.commit()
            await session.refresh(order)

            await CouponService.record_redemption(
                session,
                user_id=user.user_id,
                mirror_bot_id=user.mirror_bot_id,
                order=order,
                application=pricing,
            )
            activation_rows = (await session.execute(select(UserCoupon))).scalars().all()
            self.assertTrue(activation_rows[0].is_used)
            self.assertEqual(activation_rows[0].order_id, order.id)

    async def test_coupon_limits_block_reuse(self) -> None:
        async with self.session_maker() as session:
            user = User(
                user_id=20202,
                username="buyer2",
                mirror_bot_id=1,
                referral_link="buyer-link-2",
            )
            coupon = Coupon(
                code="ONCEONLY",
                discount_type="fixed",
                discount_value=Decimal("7.00"),
                is_active=True,
                max_uses_per_user=1,
            )
            session.add_all([user, coupon])
            await session.commit()
            await session.refresh(coupon)

            session.add(
                CouponRedemption(
                    coupon_id=coupon.id,
                    user_id=user.user_id,
                    original_amount=Decimal("20.00"),
                    discount_amount=Decimal("7.00"),
                    final_amount=Decimal("13.00"),
                )
            )
            await session.commit()

            pricing = await CouponService.calculate_discount(
                session,
                user_id=user.user_id,
                category="lookup",
                service_name="another",
                amount=Decimal("25.00"),
                coupon_code="ONCEONLY",
            )
            self.assertFalse(pricing.applied)
            self.assertEqual(pricing.message, "Coupon already used by this user")

            redemption_count = (
                await session.execute(select(CouponRedemption).where(CouponRedemption.user_id == user.user_id))
            ).scalars().all()
            self.assertEqual(len(redemption_count), 1)

    async def test_activate_coupon_blocks_duplicate_activation(self) -> None:
        async with self.session_maker() as session:
            user = User(
                user_id=30303,
                username="buyer3",
                mirror_bot_id=1,
                referral_link="buyer-link-3",
            )
            coupon = Coupon(
                code="DUPLICATE",
                discount_type="fixed",
                discount_value=Decimal("5.00"),
                is_active=True,
            )
            session.add_all([user, coupon])
            await session.commit()

            first = await CouponService.activate_coupon(session, user=user, code="duplicate")
            second = await CouponService.activate_coupon(session, user=user, code="duplicate")

            self.assertEqual(first.message, "Coupon applied")
            self.assertEqual(second.message, "Coupon already activated by this user")
            activation_rows = (await session.execute(select(UserCoupon))).scalars().all()
            self.assertEqual(len(activation_rows), 1)
