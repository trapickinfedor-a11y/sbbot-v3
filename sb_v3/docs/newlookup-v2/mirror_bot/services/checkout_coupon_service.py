from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from mirror_bot.services.order_service import OrderService
from mirror_bot.services.user_service import UserService
from shared.database.models import UserCoupon


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class CheckoutCouponService:
    @staticmethod
    async def get_available_user_coupons(
        session: AsyncSession,
        *,
        telegram_user_id: int,
        mirror_bot_id: int,
    ) -> list[UserCoupon]:
        user = await UserService.get_user(session, telegram_user_id, mirror_bot_id)
        if not user:
            return []
        result = await session.execute(
            select(UserCoupon)
            .options(selectinload(UserCoupon.coupon))
            .where(
                UserCoupon.user_id == user.id,
                UserCoupon.is_used == False,
            )
            .order_by(UserCoupon.activated_at.desc(), UserCoupon.id.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_selected_coupon(
        session: AsyncSession,
        *,
        telegram_user_id: int,
        mirror_bot_id: int,
        user_coupon_id: int,
    ) -> Optional[UserCoupon]:
        user = await UserService.get_user(session, telegram_user_id, mirror_bot_id)
        if not user:
            return None
        return await session.scalar(
            select(UserCoupon)
            .options(selectinload(UserCoupon.coupon))
            .where(
                UserCoupon.id == user_coupon_id,
                UserCoupon.user_id == user.id,
                UserCoupon.is_used == False,
            )
        )

    @staticmethod
    async def get_checkout_pricing(
        session: AsyncSession,
        *,
        telegram_user_id: int,
        state_data: dict[str, Any],
    ):
        return await OrderService.get_order_pricing(
            session,
            user_id=telegram_user_id,
            category=state_data["checkout_category"],
            service_name=state_data["checkout_service_name"],
            amount=_to_decimal(state_data["checkout_base_price"]),
            coupon_code=state_data.get("selected_coupon_code"),
            allow_auto_coupon=False,
        )

    @staticmethod
    async def render_confirmation_text(
        session: AsyncSession,
        *,
        telegram_user_id: int,
        mirror_bot_id: int,
        state_data: dict[str, Any],
    ) -> str:
        base_text = state_data.get("checkout_confirm_text") or ""
        pricing = await CheckoutCouponService.get_checkout_pricing(
            session,
            telegram_user_id=telegram_user_id,
            state_data=state_data,
        )
        coupons = await CheckoutCouponService.get_available_user_coupons(
            session,
            telegram_user_id=telegram_user_id,
            mirror_bot_id=mirror_bot_id,
        )
        lines = []
        if coupons:
            lines.append(f"🎟 Activated coupons: {len(coupons)}")
            if pricing.applied:
                lines.append(f"Selected coupon: `{pricing.code}`")
                lines.append(
                    f"Price update: ${pricing.original_amount:.2f} -> ${pricing.final_amount:.2f} "
                    f"(-${pricing.discount_amount:.2f})"
                )
            else:
                lines.append("No coupon selected for this purchase.")
        if not lines:
            return base_text
        return f"{base_text}\n\n" + "\n".join(lines)
