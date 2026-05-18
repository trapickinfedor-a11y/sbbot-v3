"""Marketer service — registration, tier system, bot stats"""
from __future__ import annotations
import secrets
import string
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import date, timedelta
from decimal import Decimal

from shared.database.models import Marketer, MarketerStats, MarketerOwnBot


TIERS = [
    {"min_users": 0, "max_users": 499, "percent": 7, "display_percent": 9, "name": "Старт", "icon": "🥉"},
    {"min_users": 500, "max_users": 4999, "percent": 9, "display_percent": 12, "name": "Продвинутый", "icon": "🥈"},
    {"min_users": 5000, "max_users": None, "percent": 12, "display_percent": 15, "name": "Элита", "icon": "🥇"},
]


def get_tier(total_users: int) -> dict:
    for tier in reversed(TIERS):
        if total_users >= tier["min_users"]:
            return tier
    return TIERS[0]


def get_next_tier(total_users: int) -> Optional[dict]:
    current = get_tier(total_users)
    idx = TIERS.index(current)
    if idx + 1 < len(TIERS):
        return TIERS[idx + 1]
    return None


def generate_promo_code(length: int = 8) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


async def get_or_create_marketer(
    session: AsyncSession,
    telegram_id: int,
    username: str = None,
    display_name: str = None,
) -> Marketer:
    result = await session.execute(
        select(Marketer).where(Marketer.telegram_id == telegram_id)
    )
    marketer = result.scalar_one_or_none()
    if marketer:
        changed = False
        if username and marketer.username != username:
            marketer.username = username
            changed = True
        if display_name and marketer.display_name != display_name:
            marketer.display_name = display_name
            changed = True
        if changed:
            await session.commit()
        return marketer

    for _ in range(10):
        promo = generate_promo_code()
        exists = await session.execute(
            select(Marketer).where(Marketer.promo_code == promo)
        )
        if not exists.scalar_one_or_none():
            break
    else:
        promo = generate_promo_code(12)

    marketer = Marketer(
        telegram_id=telegram_id,
        username=username,
        display_name=display_name,
        promo_code=promo,
    )
    session.add(marketer)
    await session.commit()
    await session.refresh(marketer)
    return marketer


async def get_marketer_bots(session: AsyncSession, marketer_id: int) -> list[MarketerOwnBot]:
    r = await session.execute(
        select(MarketerOwnBot)
        .where(MarketerOwnBot.marketer_id == marketer_id)
        .order_by(MarketerOwnBot.created_at.desc())
    )
    return list(r.scalars().all())


async def get_total_users_across_bots(session: AsyncSession, marketer_id: int) -> int:
    r = await session.execute(
        select(func.coalesce(func.sum(MarketerOwnBot.total_users), 0))
        .where(MarketerOwnBot.marketer_id == marketer_id)
    )
    return int(r.scalar() or 0)


async def get_total_earned_across_bots(session: AsyncSession, marketer_id: int) -> Decimal:
    r = await session.execute(
        select(func.coalesce(func.sum(MarketerOwnBot.total_earned), 0))
        .where(MarketerOwnBot.marketer_id == marketer_id)
    )
    return Decimal(str(r.scalar() or 0))


async def get_total_orders_across_bots(session: AsyncSession, marketer_id: int) -> int:
    r = await session.execute(
        select(func.coalesce(func.sum(MarketerOwnBot.total_orders), 0))
        .where(MarketerOwnBot.marketer_id == marketer_id)
    )
    return int(r.scalar() or 0)


async def update_marketer_tier(session: AsyncSession, marketer: Marketer) -> dict:
    total_users = await get_total_users_across_bots(session, marketer.id)
    tier = get_tier(total_users)
    if marketer.reward_percent != tier["percent"]:
        marketer.reward_percent = tier["percent"]
        await session.commit()
    return tier


async def get_today_stats(session: AsyncSession, marketer_id: int) -> dict:
    today = date.today()
    result = await session.execute(
        select(MarketerStats).where(
            and_(MarketerStats.marketer_id == marketer_id, MarketerStats.date == today)
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        return {
            "registrations": 0, "first_topups": 0, "topup_amount": 0,
            "earned": 0, "buyers_count": 0, "sales_count": 0,
        }
    return {
        "registrations": row.registrations,
        "first_topups": row.first_topups,
        "topup_amount": float(row.topup_amount or 0),
        "earned": float(row.earned or 0),
        "buyers_count": int(getattr(row, "buyers_count", 0) or 0),
        "sales_count": int(getattr(row, "sales_count", 0) or 0),
    }


async def get_30day_stats(session: AsyncSession, marketer_id: int) -> dict:
    since = date.today() - timedelta(days=30)
    result = await session.execute(
        select(
            func.sum(MarketerStats.registrations).label("reg"),
            func.sum(MarketerStats.first_topups).label("ft"),
            func.sum(MarketerStats.topup_amount).label("ta"),
            func.sum(MarketerStats.earned).label("earned"),
            func.sum(MarketerStats.buyers_count).label("bc"),
            func.sum(MarketerStats.sales_count).label("sc"),
        ).where(
            and_(MarketerStats.marketer_id == marketer_id, MarketerStats.date >= since)
        )
    )
    row = result.one()
    return {
        "registrations": row.reg or 0,
        "first_topups": row.ft or 0,
        "topup_amount": float(row.ta or 0),
        "earned": float(row.earned or 0),
        "buyers_count": int(row.bc or 0),
        "sales_count": int(row.sc or 0),
    }
