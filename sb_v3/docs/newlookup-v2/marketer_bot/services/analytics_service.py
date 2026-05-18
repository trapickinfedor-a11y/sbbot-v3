"""Analytics service — period stats, per-bot breakdown, trends, daily report (i18n)"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from shared.database.models import MarketerStats, MarketerOwnBot


PERIOD_DAYS = {"day": 1, "week": 7, "month": 30, "all": 3650}


def _period_label(period: str, t) -> str:
    return {"day": t.PERIOD_DAY, "week": t.PERIOD_WEEK, "month": t.PERIOD_MONTH, "all": t.PERIOD_ALL}.get(period, period)


async def get_period_stats(session: AsyncSession, marketer_id: int, period: str) -> dict:
    days = PERIOD_DAYS.get(period, 30)
    since = date.today() if period == "day" else date.today() - timedelta(days=days)

    result = await session.execute(
        select(
            func.coalesce(func.sum(MarketerStats.registrations), 0).label("registrations"),
            func.coalesce(func.sum(MarketerStats.first_topups), 0).label("first_topups"),
            func.coalesce(func.sum(MarketerStats.topup_amount), 0).label("topup_amount"),
            func.coalesce(func.sum(MarketerStats.earned), 0).label("earned"),
            func.coalesce(func.sum(MarketerStats.buyers_count), 0).label("buyers_count"),
            func.coalesce(func.sum(MarketerStats.sales_count), 0).label("sales_count"),
            func.count(MarketerStats.id).label("days_with_data"),
        ).where(and_(MarketerStats.marketer_id == marketer_id, MarketerStats.date >= since))
    )
    row = result.one()
    earned = float(row.earned or 0)
    registrations = int(row.registrations or 0)
    sales = int(row.sales_count or 0)
    buyers = int(row.buyers_count or 0)
    topup = float(row.topup_amount or 0)
    dwd = int(row.days_with_data or 0)

    return {
        "registrations": registrations,
        "first_topups": int(row.first_topups or 0),
        "topup_amount": topup,
        "earned": earned,
        "buyers_count": buyers,
        "sales_count": sales,
        "days_with_data": dwd,
        "avg_daily_earned": earned / dwd if dwd else 0,
        "avg_daily_reg": registrations / dwd if dwd else 0,
        "conversion_pct": round(buyers / registrations * 100, 1) if registrations else 0,
        "avg_check": round(topup / buyers, 2) if buyers else 0,
    }


async def get_daily_trend(session: AsyncSession, marketer_id: int, days: int = 7) -> list[dict]:
    since = date.today() - timedelta(days=days - 1)
    result = await session.execute(
        select(MarketerStats)
        .where(and_(MarketerStats.marketer_id == marketer_id, MarketerStats.date >= since))
        .order_by(MarketerStats.date.asc())
    )
    by_date = {}
    for r in result.scalars().all():
        by_date[r.date] = {
            "date": r.date,
            "registrations": r.registrations,
            "earned": float(r.earned or 0),
            "sales": int(getattr(r, "sales_count", 0) or 0),
            "buyers": int(getattr(r, "buyers_count", 0) or 0),
            "topup": float(r.topup_amount or 0),
        }
    trend = []
    for i in range(days):
        d = since + timedelta(days=i)
        trend.append(by_date.get(d, {"date": d, "registrations": 0, "earned": 0, "sales": 0, "buyers": 0, "topup": 0}))
    return trend


async def get_per_bot_stats(session: AsyncSession, marketer_id: int) -> list[dict]:
    result = await session.execute(
        select(MarketerOwnBot)
        .where(MarketerOwnBot.marketer_id == marketer_id)
        .order_by(MarketerOwnBot.total_users.desc())
    )
    bots = list(result.scalars().all())
    total_u = sum(b.total_users for b in bots) or 1
    return [
        {
            "username": b.bot_username or "?",
            "is_active": b.is_active,
            "users": b.total_users,
            "orders": b.total_orders,
            "earned": float(b.total_earned or 0),
            "share_pct": round(b.total_users / total_u * 100, 1),
            "last_activity": b.last_activity_at,
        }
        for b in bots
    ]


def _spark(values: list[float], width: int = 7) -> str:
    if not values or all(v == 0 for v in values):
        return "▁" * width
    mn, mx = min(values), max(values)
    blocks = "▁▂▃▄▅▆▇█"
    span = mx - mn if mx != mn else 1
    return "".join(blocks[min(int((v - mn) / span * 7), 7)] for v in values[-width:])


def _bar(value: float, max_val: float, width: int = 10) -> str:
    if max_val <= 0:
        return "░" * width
    filled = int(value / max_val * width)
    return "█" * filled + "░" * (width - filled)


async def build_analytics_text(session: AsyncSession, marketer_id: int, period: str, t) -> str:
    label = _period_label(period, t)
    stats = await get_period_stats(session, marketer_id, period)
    trend = await get_daily_trend(session, marketer_id, days=7 if period in ("day", "week") else 14)

    se = _spark([d["earned"] for d in trend])
    sr = _spark([float(d["registrations"]) for d in trend])
    ss = _spark([float(d["sales"]) for d in trend])

    return (
        f"{t.ANALYTICS_TITLE.format(period=label)}\n\n"
        f"{t.REGISTRATIONS}: <b>{stats['registrations']}</b>\n"
        f"   {sr}  {t.TREND_LABEL}\n"
        f"{t.EARNED}: <b>${stats['earned']:.2f}</b>\n"
        f"   {se}  {t.TREND_LABEL}\n"
        f"{t.SALES}: <b>{stats['sales_count']}</b>\n"
        f"   {ss}  {t.TREND_LABEL}\n"
        f"{t.BUYERS}: <b>{stats['buyers_count']}</b>\n"
        f"{t.TOPUP_AMOUNT}: <b>${stats['topup_amount']:.2f}</b>\n\n"
        f"<b>{t.EFFICIENCY}:</b>\n"
        f"{t.CONVERSION}: <b>{stats['conversion_pct']}%</b>\n"
        f"{t.AVG_CHECK}: <b>${stats['avg_check']:.2f}</b>\n"
        f"{t.AVG_DAILY}: <b>${stats['avg_daily_earned']:.2f}</b> | "
        f"<b>{stats['avg_daily_reg']:.1f}</b> {t.AVG_REG}"
    )


async def build_per_bot_text(session: AsyncSession, marketer_id: int, t) -> str:
    bots = await get_per_bot_stats(session, marketer_id)
    if not bots:
        return f"{t.BOTS_STATS_TITLE}\n\n{t.NO_DATA}"

    max_u = max(b["users"] for b in bots) or 1
    max_e = max(b["earned"] for b in bots) or 1

    lines = []
    for i, b in enumerate(bots, 1):
        status = "✅" if b["is_active"] else "❌"
        bar_u = _bar(b["users"], max_u, 8)
        bar_e = _bar(b["earned"], max_e, 8)
        last = b["last_activity"].strftime("%d.%m %H:%M") if b["last_activity"] else "—"
        lines.append(
            f"{status} <b>{i}. @{b['username']}</b>\n"
            f"   👥 {b['users']} ({b['share_pct']}%)  {bar_u}\n"
            f"   💰 ${b['earned']:.2f}  {bar_e}\n"
            f"   🛒 {b['orders']} | {t.LAST_ACTIVITY}: {last}"
        )

    total_u = sum(b["users"] for b in bots)
    total_e = sum(b["earned"] for b in bots)
    total_o = sum(b["orders"] for b in bots)

    text = (
        f"{t.BOTS_STATS_TITLE} ({len(bots)})\n\n"
        + "\n\n".join(lines)
        + f"\n\n<b>{t.BOTS_TOTAL}:</b> 👥 {total_u} | 🛒 {total_o} | 💰 ${total_e:.2f}"
    )
    return text[:4000]


async def build_trend_text(session: AsyncSession, marketer_id: int, days: int, t) -> str:
    trend = await get_daily_trend(session, marketer_id, days=days)
    if not trend:
        return f"{t.TREND_TITLE.format(days=days)}\n\n{t.NO_DATA}"

    max_e = max(d["earned"] for d in trend) or 1
    lines = []
    for d in trend:
        dl = d["date"].strftime("%d.%m")
        bar = _bar(d["earned"], max_e, 8)
        lines.append(f"<code>{dl}</code> {bar} ${d['earned']:.0f} | 👥{d['registrations']} | 🛒{d['sales']}")

    te = sum(d["earned"] for d in trend)
    tr = sum(d["registrations"] for d in trend)
    ts = sum(d["sales"] for d in trend)

    text = (
        f"{t.TREND_TITLE.format(days=days)}\n"
        f"{t.TREND_HEADER}\n\n"
        + "\n".join(lines)
        + f"\n\n<b>{t.BOTS_TOTAL}:</b> 💰 ${te:.2f} | 👥 {tr} | 🛒 {ts}"
    )
    return text[:4000]


async def build_daily_report(session: AsyncSession, marketer_id: int, t) -> str:
    from marketer_bot.services.marketer_service import (
        get_total_users_across_bots,
        get_total_earned_across_bots,
        get_total_orders_across_bots,
        get_tier,
        get_next_tier,
    )

    today_stats = await get_period_stats(session, marketer_id, "day")
    week_stats = await get_period_stats(session, marketer_id, "week")
    trend = await get_daily_trend(session, marketer_id, days=7)
    bots = await get_per_bot_stats(session, marketer_id)

    total_users = await get_total_users_across_bots(session, marketer_id)
    total_earned = await get_total_earned_across_bots(session, marketer_id)
    total_orders = await get_total_orders_across_bots(session, marketer_id)
    tier = get_tier(total_users)
    next_tier = get_next_tier(total_users)

    se = _spark([d["earned"] for d in trend])
    sr = _spark([float(d["registrations"]) for d in trend])

    text = f"{t.DAILY_TITLE.format(date=date.today().strftime('%d.%m.%Y'))}\n\n"
    text += f"{tier['icon']} {t.TIER_LEVEL}: <b>{tier['name']}</b> — {tier['display_percent']}%\n"
    if next_tier:
        left = next_tier["min_users"] - total_users
        text += t.TIER_NEXT.format(name=next_tier["name"], percent=next_tier["display_percent"], left=left) + "\n"
    text += "\n"

    text += (
        f"<b>{t.DAILY_TODAY}:</b>\n"
        f"  {t.REGISTRATIONS}: <b>{today_stats['registrations']}</b>\n"
        f"  {t.SALES}: <b>{today_stats['sales_count']}</b>\n"
        f"  {t.BUYERS}: <b>{today_stats['buyers_count']}</b>\n"
        f"  {t.EARNED}: <b>${today_stats['earned']:.2f}</b>\n"
        f"  {t.CONVERSION}: <b>{today_stats['conversion_pct']}%</b>\n\n"
    )

    text += (
        f"<b>{t.DAILY_WEEK}:</b>\n"
        f"  {t.REGISTRATIONS}: {week_stats['registrations']} | {t.SALES}: {week_stats['sales_count']}\n"
        f"  💰 ${week_stats['earned']:.2f} | {t.AVG_DAILY}: ${week_stats['avg_daily_earned']:.2f}\n"
        f"  {t.CONVERSION}: {week_stats['conversion_pct']}%\n"
        f"  {se} {t.EARNED}  {sr} {t.REGISTRATIONS}\n\n"
    )

    if bots:
        max_u = max(b["users"] for b in bots) or 1
        text += f"<b>{t.DAILY_BOTS}:</b>\n"
        for b in bots[:10]:
            status = "✅" if b["is_active"] else "❌"
            bar = _bar(b["users"], max_u, 6)
            text += f"  {status} @{b['username']}  {bar} {b['users']} {t.USERS_SHORT} ${b['earned']:.2f}\n"
        text += "\n"

    text += (
        f"<b>{t.DAILY_TOTALS}:</b>\n"
        f"👥 {total_users} | 🛒 {total_orders} | 💰 ${float(total_earned):.2f}"
    )
    return text[:4000]
