"""Shared referral service — reusable across all bots."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import (
    Marketer,
    Referral,
    ReferralReward,
    ReferralSettings,
    ReferralWithdrawal,
)

logger = logging.getLogger(__name__)

# Default settings (fallback if no DB row)
_DEFAULT_SETTINGS = {
    "level1_display_pct": 15.0,
    "level1_real_pct": 7.0,
    "level2_display_pct": 7.0,
    "level2_real_pct": 3.0,
    "level3_display_pct": 3.0,
    "level3_real_pct": 1.0,
    "level4_display_pct": 1.0,
    "level4_real_pct": 0.2,
    "max_daily_referrals": 50,
    "min_purchase_usd": 1.0,
    "min_withdrawal_usd": 10.0,
}


def generate_ref_code(telegram_id: int) -> str:
    """Generate referral code for a given Telegram user ID."""
    return f"ref_{telegram_id}"


def parse_ref_code(code: str) -> Optional[int]:
    """Parse ref_USERID from a start parameter. Returns telegram_id or None."""
    if code and code.startswith("ref_"):
        try:
            return int(code[4:])
        except ValueError:
            return None
    return None


async def _get_settings(session: AsyncSession) -> ReferralSettings:
    """Get or create default referral settings."""
    result = await session.execute(select(ReferralSettings).where(ReferralSettings.id == 1))
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = ReferralSettings(id=1)
        session.add(settings)
        await session.flush()
    return settings


class ReferralService:
    """Centralised referral logic used by all bots."""

    generate_ref_code = staticmethod(generate_ref_code)
    parse_ref_code = staticmethod(parse_ref_code)

    @staticmethod
    async def create_referral(
        session: AsyncSession,
        referrer_telegram_id: int,
        referred_telegram_id: int,
    ) -> Optional[Referral]:
        """Register a referral link between two Telegram users.

        Returns the created Referral row, or None if the link already exists
        or the referred user is trying to refer themselves.
        """
        if referrer_telegram_id == referred_telegram_id:
            return None

        # Check duplicate
        existing = await session.execute(
            select(Referral).where(
                Referral.referrer_id == referrer_telegram_id,
                Referral.referred_id == referred_telegram_id,
            )
        )
        if existing.scalar_one_or_none():
            return None

        # Anti-fraud: daily limit check
        settings = await _get_settings(session)
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        count_result = await session.execute(
            select(func.count(Referral.id)).where(
                Referral.referrer_id == referrer_telegram_id,
                Referral.created_at >= today_start,
            )
        )
        today_count = count_result.scalar_one() or 0
        if today_count >= settings.max_daily_referrals:
            logger.warning(
                "Daily referral limit reached for referrer %s", referrer_telegram_id
            )
            return None

        ref = Referral(
            referrer_id=referrer_telegram_id,
            referred_id=referred_telegram_id,
        )
        session.add(ref)
        await session.flush()
        return ref

    @staticmethod
    async def process_purchase_rewards(
        session: AsyncSession,
        buyer_telegram_id: int,
        purchase_amount_usd: float,
    ) -> list[ReferralReward]:
        """Create referral rewards up to 4 levels for a purchase.

        Returns the list of created reward rows.
        """
        settings = await _get_settings(session)
        if purchase_amount_usd < settings.min_purchase_usd:
            return []

        display_pcts = [
            settings.level1_display_pct,
            settings.level2_display_pct,
            settings.level3_display_pct,
            settings.level4_display_pct,
        ]
        real_pcts = [
            settings.level1_real_pct,
            settings.level2_real_pct,
            settings.level3_real_pct,
            settings.level4_real_pct,
        ]

        rewards: list[ReferralReward] = []
        current_referred = buyer_telegram_id

        for level in range(1, 5):
            ref_row = await session.execute(
                select(Referral).where(Referral.referred_id == current_referred)
            )
            ref = ref_row.scalar_one_or_none()
            if ref is None:
                break

            referrer_tid = ref.referrer_id
            d_pct = display_pcts[level - 1]
            r_pct = real_pcts[level - 1]

            reward = ReferralReward(
                referrer_id=referrer_tid,
                referred_user_id=buyer_telegram_id,
                referral_id=ref.id,
                amount_display=Decimal(str(round(purchase_amount_usd * d_pct / 100, 2))),
                amount_real=Decimal(str(round(purchase_amount_usd * r_pct / 100, 2))),
                level=level,
                source="purchase",
                status="pending_moderation",
            )
            session.add(reward)
            rewards.append(reward)

            current_referred = referrer_tid

        await session.flush()
        return rewards

    @staticmethod
    async def get_referral_stats(
        session: AsyncSession,
        referrer_telegram_id: int,
    ) -> dict:
        """Return aggregate referral stats for a marketer."""
        # Total invited
        invited_result = await session.execute(
            select(func.count(Referral.id)).where(
                Referral.referrer_id == referrer_telegram_id
            )
        )
        total_invited = invited_result.scalar_one() or 0

        # Total rewards
        rewards_result = await session.execute(
            select(
                func.count(ReferralReward.id),
                func.sum(ReferralReward.amount_display),
                func.sum(ReferralReward.amount_real),
            ).where(ReferralReward.referrer_id == referrer_telegram_id)
        )
        row = rewards_result.one()
        total_rewards = row[0] or 0
        total_display = float(row[1] or 0)
        total_real = float(row[2] or 0)

        # Pending moderation
        pending_result = await session.execute(
            select(func.sum(ReferralReward.amount_display)).where(
                ReferralReward.referrer_id == referrer_telegram_id,
                ReferralReward.status == "pending_moderation",
            )
        )
        pending = float(pending_result.scalar_one() or 0)

        # Approved (confirmed)
        approved_result = await session.execute(
            select(func.count(ReferralReward.id)).where(
                ReferralReward.referrer_id == referrer_telegram_id,
                ReferralReward.status.in_(["approved", "paid"]),
            )
        )
        confirmed = approved_result.scalar_one() or 0

        return {
            "total_invited": total_invited,
            "confirmed": confirmed,
            "total_earned_display": total_display,
            "total_earned_real": total_real,
            "pending_moderation": pending,
            "total_rewards": total_rewards,
        }

    @staticmethod
    async def get_referral_history(
        session: AsyncSession,
        referrer_telegram_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[ReferralReward]:
        """Return paginated list of referral reward records."""
        result = await session.execute(
            select(ReferralReward)
            .where(ReferralReward.referrer_id == referrer_telegram_id)
            .order_by(ReferralReward.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    @staticmethod
    async def request_referral_withdrawal(
        session: AsyncSession,
        referrer_telegram_id: int,
        amount_usd: float,
        requisites: str,
    ) -> Optional[ReferralWithdrawal]:
        """Create a referral withdrawal request."""
        settings = await _get_settings(session)
        if amount_usd < settings.min_withdrawal_usd:
            return None

        withdrawal = ReferralWithdrawal(
            referrer_id=referrer_telegram_id,
            amount=Decimal(str(round(amount_usd, 2))),
            requisites=requisites,
            status="pending_moderation",
        )
        session.add(withdrawal)
        await session.flush()
        return withdrawal

    @staticmethod
    async def get_withdrawal_history(
        session: AsyncSession,
        referrer_telegram_id: int,
        limit: int = 15,
    ) -> list[ReferralWithdrawal]:
        """Return withdrawal history for a referrer."""
        result = await session.execute(
            select(ReferralWithdrawal)
            .where(ReferralWithdrawal.referrer_id == referrer_telegram_id)
            .order_by(ReferralWithdrawal.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_available_balance(
        session: AsyncSession,
        referrer_telegram_id: int,
    ) -> Decimal:
        """Return approved (real) balance available for withdrawal."""
        result = await session.execute(
            select(func.sum(ReferralReward.amount_real)).where(
                ReferralReward.referrer_id == referrer_telegram_id,
                ReferralReward.status == "approved",
            )
        )
        earned = result.scalar_one() or Decimal("0")

        withdrawn = await session.execute(
            select(func.sum(ReferralWithdrawal.amount)).where(
                ReferralWithdrawal.referrer_id == referrer_telegram_id,
                ReferralWithdrawal.status.in_(["pending_moderation", "approved"]),
            )
        )
        total_withdrawn = withdrawn.scalar_one() or Decimal("0")

        balance = Decimal(str(earned)) - Decimal(str(total_withdrawn))
        return max(balance, Decimal("0"))

    @staticmethod
    async def get_settings(session: AsyncSession) -> ReferralSettings:
        """Public accessor for referral settings."""
        return await _get_settings(session)
