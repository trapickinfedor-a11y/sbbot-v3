"""Сервис владельцев ботов: статистика, выводы"""
import calendar
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from shared.database.models import (
    MirrorBot, BotOwner, BotOwnerStats, BotOwnerWithdrawal,
    SystemSetting,
    User, Order, Transaction
)

DISPLAY_PERCENT = 10  # Показываем владельцу 10%
REAL_PERCENT = 7  # Реально начисляем 7%
MIN_WITHDRAWAL = 100


async def get_min_withdrawal_amount(session: AsyncSession) -> float:
    row = await session.scalar(select(SystemSetting).where(SystemSetting.key == "MIN_WITHDRAWAL_AMOUNT"))
    try:
        return float(row.value) if row and row.value is not None else float(MIN_WITHDRAWAL)
    except (TypeError, ValueError):
        return float(MIN_WITHDRAWAL)


async def get_or_create_owner(session: AsyncSession, owner_user_id: int) -> BotOwner:
    result = await session.execute(select(BotOwner).where(BotOwner.owner_user_id == owner_user_id))
    owner = result.scalar_one_or_none()
    if not owner:
        owner = BotOwner(owner_user_id=owner_user_id)
        session.add(owner)
        await session.flush()
        await session.refresh(owner)
    return owner


async def get_owner_stats(
    session: AsyncSession,
    owner_user_id: int,
) -> Dict:
    """Агрегированная статистика по всем ботам владельца"""
    # Боты владельца
    bots_result = await session.execute(
        select(MirrorBot.id).where(
            MirrorBot.owner_user_id == owner_user_id,
            MirrorBot.is_active == True
        )
    )
    bot_ids = [r[0] for r in bots_result.all()]

    owner = await get_or_create_owner(session, owner_user_id)
    min_withdrawal = await get_min_withdrawal_amount(session)

    if not bot_ids:
        return {
            "balance": float(owner.balance or 0),
            "total_earned": float(owner.total_earned or 0),
            "total_withdrawn": float(owner.total_withdrawn or 0),
            "spent_today": 0,
            "spent_week": 0,
            "spent_month": 0,
            "topped_up_today": 0,
            "topped_up_week": 0,
            "topped_up_month": 0,
            "income_today": 0,
            "income_week": 0,
            "income_month": 0,
            "income_total": float(owner.total_earned or 0),
            "display_percent": DISPLAY_PERCENT,
            "min_withdrawal": min_withdrawal,
        }

    today = date.today()
    week_start = today - timedelta(days=7)
    month_start = today - timedelta(days=30)

    async def _agg(start_date, end_date=None):
        q = select(
            func.sum(BotOwnerStats.spent).label("s"),
            func.sum(BotOwnerStats.topped_up).label("t"),
            func.sum(BotOwnerStats.owner_income).label("i"),
        ).where(
            BotOwnerStats.mirror_bot_id.in_(bot_ids),
            BotOwnerStats.date >= start_date
        )
        if end_date:
            q = q.where(BotOwnerStats.date <= end_date)
        r = await session.execute(q)
        row = r.one()
        return (
            float(row.s or 0),
            float(row.t or 0),
            float(row.i or 0),
        )

    spent_today, topped_today, income_today = await _agg(today)
    spent_week, topped_week, income_week = await _agg(week_start)
    spent_month, topped_month, income_month = await _agg(month_start)

    return {
        "balance": float(owner.balance or 0),
        "total_earned": float(owner.total_earned or 0),
        "total_withdrawn": float(owner.total_withdrawn or 0),
        "spent_today": spent_today,
        "spent_week": spent_week,
        "spent_month": spent_month,
        "topped_up_today": topped_today,
        "topped_up_week": topped_week,
        "topped_up_month": topped_month,
        "income_today": income_today,
        "income_week": income_week,
        "income_month": income_month,
        "income_total": float(owner.total_earned or 0),
        "display_percent": DISPLAY_PERCENT,
        "min_withdrawal": min_withdrawal,
    }


async def get_owner_month_topups_chart(
    session: AsyncSession,
    owner_user_id: int,
    target_date: Optional[date] = None,
) -> Dict:
    """Дневные суммы пополнений за текущий месяц по всем ботам владельца."""
    current = target_date or date.today()
    month_start = current.replace(day=1)
    last_day = calendar.monthrange(current.year, current.month)[1]
    month_end = current.replace(day=last_day)

    bots_result = await session.execute(
        select(MirrorBot.id).where(
            MirrorBot.owner_user_id == owner_user_id,
            MirrorBot.is_active == True
        )
    )
    bot_ids = [r[0] for r in bots_result.all()]

    labels = [f"{day:02d}" for day in range(1, last_day + 1)]
    values = [0.0 for _ in range(last_day)]

    if not bot_ids:
        return {
            "month_label": month_start.strftime("%m.%Y"),
            "labels": labels,
            "values": values,
            "total": 0.0,
            "max_value": 0.0,
        }

    result = await session.execute(
        select(
            BotOwnerStats.date,
            func.sum(BotOwnerStats.topped_up).label("topped_up"),
        ).where(
            BotOwnerStats.mirror_bot_id.in_(bot_ids),
            BotOwnerStats.date >= month_start,
            BotOwnerStats.date <= month_end,
        ).group_by(BotOwnerStats.date)
    )
    rows = result.all()
    for row in rows:
        day_index = row.date.day - 1
        values[day_index] = float(row.topped_up or 0)

    return {
        "month_label": month_start.strftime("%m.%Y"),
        "labels": labels,
        "values": values,
        "total": round(sum(values), 2),
        "max_value": max(values) if values else 0.0,
    }
