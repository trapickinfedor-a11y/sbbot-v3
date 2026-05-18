from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import Coupon, CouponRedemption, Order, User, UserCoupon


def _money(value: Decimal | float | int | str | None) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass
class CouponApplication:
    code: str | None
    original_amount: Decimal
    discount_amount: Decimal
    final_amount: Decimal
    coupon: Coupon | None = None
    message: str | None = None

    @property
    def applied(self) -> bool:
        return bool(self.coupon and self.discount_amount > 0)


class CouponService:
    @staticmethod
    def normalize_code(code: str | None) -> str:
        return (code or "").strip().upper()

    @staticmethod
    async def get_coupon_by_code(session: AsyncSession, code: str | None) -> Optional[Coupon]:
        normalized = CouponService.normalize_code(code)
        if not normalized:
            return None
        return await session.scalar(select(Coupon).where(Coupon.code == normalized))

    @staticmethod
    async def assign_coupon_to_user(
        session: AsyncSession,
        user: User,
        code: str | None,
    ) -> CouponApplication:
        return await CouponService.activate_coupon(session, user=user, code=code)

    @staticmethod
    async def activate_coupon(
        session: AsyncSession,
        *,
        user: User,
        code: str | None,
    ) -> CouponApplication:
        normalized = CouponService.normalize_code(code)
        if not normalized:
            user.active_coupon_code = None
            user.active_coupon_set_at = None
            await session.commit()
            return CouponApplication(
                code=None,
                original_amount=Decimal("0"),
                discount_amount=Decimal("0"),
                final_amount=Decimal("0"),
                message="Coupon cleared",
            )

        coupon = await CouponService.get_coupon_by_code(session, normalized)
        if not coupon:
            return CouponApplication(
                code=normalized,
                original_amount=Decimal("0"),
                discount_amount=Decimal("0"),
                final_amount=Decimal("0"),
                message="Coupon not found",
            )

        availability_error = await CouponService._validate_coupon_availability(
            session,
            coupon,
            user.user_id,
        )
        if availability_error:
            return CouponApplication(
                code=normalized,
                original_amount=Decimal("0"),
                discount_amount=Decimal("0"),
                final_amount=Decimal("0"),
                coupon=coupon,
                message=availability_error,
            )

        user_coupon = await session.scalar(
            select(UserCoupon).where(
                UserCoupon.user_id == user.id,
                UserCoupon.coupon_id == coupon.id,
            )
        )
        if user_coupon:
            return CouponApplication(
                code=normalized,
                original_amount=Decimal("0"),
                discount_amount=Decimal("0"),
                final_amount=Decimal("0"),
                coupon=coupon,
                message="Coupon already activated by this user",
            )

        session.add(
            UserCoupon(
                user_id=user.id,
                coupon_id=coupon.id,
                activated_at=datetime.now(timezone.utc),
                is_used=False,
            )
        )
        user.active_coupon_code = coupon.code
        user.active_coupon_set_at = datetime.now(timezone.utc)
        await session.commit()
        return CouponApplication(
            code=coupon.code,
            original_amount=Decimal("0"),
            discount_amount=Decimal("0"),
            final_amount=Decimal("0"),
            coupon=coupon,
            message="Coupon applied",
        )

    @staticmethod
    async def clear_user_coupon(session: AsyncSession, user: User) -> None:
        user.active_coupon_code = None
        user.active_coupon_set_at = None
        await session.commit()

    @staticmethod
    async def calculate_discount(
        session: AsyncSession,
        *,
        user_id: int,
        category: str,
        service_name: str,
        amount: Decimal | float | int | str,
        coupon_code: str | None = None,
        allow_auto_coupon: bool = True,
    ) -> CouponApplication:
        amount_decimal = _money(amount).quantize(Decimal("0.01"))
        normalized = CouponService.normalize_code(coupon_code)
        if not normalized and allow_auto_coupon:
            user = await session.scalar(select(User).where(User.user_id == user_id))
            if user:
                normalized = CouponService.normalize_code(getattr(user, "active_coupon_code", None))
                if normalized:
                    active_user_coupon = await session.scalar(
                        select(UserCoupon)
                        .join(Coupon, Coupon.id == UserCoupon.coupon_id)
                        .where(
                            UserCoupon.user_id == user.id,
                            UserCoupon.is_used == False,
                            Coupon.code == normalized,
                        )
                    )
                    if not active_user_coupon and getattr(user, "active_coupon_set_at", None):
                        normalized = ""

        if not normalized:
            return CouponApplication(
                code=None,
                original_amount=amount_decimal,
                discount_amount=Decimal("0.00"),
                final_amount=amount_decimal,
                message="No active coupon",
            )

        coupon = await CouponService.get_coupon_by_code(session, normalized)
        if not coupon:
            return CouponApplication(
                code=normalized,
                original_amount=amount_decimal,
                discount_amount=Decimal("0.00"),
                final_amount=amount_decimal,
                message="Coupon not found",
            )

        availability_error = await CouponService._validate_coupon_availability(
            session,
            coupon,
            user_id,
        )
        if availability_error:
            return CouponApplication(
                code=normalized,
                original_amount=amount_decimal,
                discount_amount=Decimal("0.00"),
                final_amount=amount_decimal,
                coupon=coupon,
                message=availability_error,
            )

        scope_error = CouponService._validate_coupon_scope(
            coupon,
            category=category,
            service_name=service_name,
            amount=amount_decimal,
        )
        if scope_error:
            return CouponApplication(
                code=normalized,
                original_amount=amount_decimal,
                discount_amount=Decimal("0.00"),
                final_amount=amount_decimal,
                coupon=coupon,
                message=scope_error,
            )

        if coupon.discount_type == "fixed":
            discount_amount = min(_money(coupon.discount_value), amount_decimal)
        else:
            pct = _money(coupon.discount_value) / Decimal("100")
            discount_amount = (amount_decimal * pct).quantize(Decimal("0.01"))

        final_amount = max(Decimal("0.00"), amount_decimal - discount_amount).quantize(Decimal("0.01"))
        return CouponApplication(
            code=coupon.code,
            original_amount=amount_decimal,
            discount_amount=discount_amount,
            final_amount=final_amount,
            coupon=coupon,
            message="Coupon applied",
        )

    @staticmethod
    async def record_redemption(
        session: AsyncSession,
        *,
        user_id: int,
        mirror_bot_id: int | None,
        order: Order,
        application: CouponApplication,
        commit: bool = True,
    ) -> Optional[CouponRedemption]:
        if not application.applied or not application.coupon:
            return None

        redemption = CouponRedemption(
            coupon_id=application.coupon.id,
            user_id=user_id,
            order_id=order.id,
            mirror_bot_id=mirror_bot_id,
            category=order.category,
            service_name=order.service_name,
            original_amount=application.original_amount,
            discount_amount=application.discount_amount,
            final_amount=application.final_amount,
        )
        session.add(redemption)

        user = await session.scalar(select(User).where(User.user_id == user_id))
        if user and application.coupon:
            user_coupon = await session.scalar(
                select(UserCoupon).where(
                    UserCoupon.user_id == user.id,
                    UserCoupon.coupon_id == application.coupon.id,
                    UserCoupon.is_used == False,
                )
            )
            if user_coupon:
                user_coupon.is_used = True
                user_coupon.order_id = order.id
                user_coupon.used_at = datetime.now(timezone.utc)
        if user and CouponService.normalize_code(user.active_coupon_code) == application.code:
            user.active_coupon_code = None
            user.active_coupon_set_at = None
        await session.flush()
        if commit:
            await session.commit()
            await session.refresh(redemption)
        return redemption

    @staticmethod
    async def _validate_coupon_availability(
        session: AsyncSession,
        coupon: Coupon,
        user_id: int,
    ) -> Optional[str]:
        now = datetime.now(timezone.utc)
        if not coupon.is_active:
            return "Coupon is disabled"
        if coupon.starts_at and coupon.starts_at > now:
            return "Coupon is not active yet"
        if coupon.ends_at and coupon.ends_at < now:
            return "Coupon has expired"

        if coupon.max_total_uses is not None:
            total_uses = await session.scalar(
                select(func.count(CouponRedemption.id)).where(CouponRedemption.coupon_id == coupon.id)
            ) or 0
            if total_uses >= coupon.max_total_uses:
                return "Coupon usage limit reached"

        if coupon.max_uses_per_user is not None:
            user_uses = await session.scalar(
                select(func.count(CouponRedemption.id)).where(
                    CouponRedemption.coupon_id == coupon.id,
                    CouponRedemption.user_id == user_id,
                )
            ) or 0
            if user_uses >= coupon.max_uses_per_user:
                return "Coupon already used by this user"

        return None


    @staticmethod
    def _validate_coupon_scope(
        coupon: Coupon,
        *,
        category: str,
        service_name: str,
        amount: Decimal,
    ) -> Optional[str]:
        categories = {str(item).strip().lower() for item in (coupon.allowed_categories or []) if item}
        services = {str(item).strip().lower() for item in (coupon.allowed_services or []) if item}
        normalized_category = (category or "").strip().lower()
        normalized_service = (service_name or "").strip().lower()

        if coupon.min_order_amount is not None and amount < _money(coupon.min_order_amount):
            return "Order amount is too low for this coupon"
        if categories and normalized_category not in categories:
            return "Coupon is not valid for this category"
        if services and normalized_service not in services:
            return "Coupon is not valid for this service"
        return None
