from __future__ import annotations

import logging
import os
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import Marketer, MarketerActivityLog, MarketerBotLink, MarketerStats, MarketerWithdrawal, MirrorBot, User
from shared.services.admin_notification_service import AdminNotificationService
from shared.services.bot_pool import get_bot
from shared.services.marketer_activity_log import log_marketer_activity

logger = logging.getLogger(__name__)

REGISTRATION_MILESTONE_STEP = 50
AUTO_BLOCK_SHARE_THRESHOLD = Decimal("0.90")


async def get_or_create_marketer_stats_row(
    session: AsyncSession,
    marketer_id: int,
    target_date: date | None = None,
) -> MarketerStats:
    stats_date = target_date or date.today()
    result = await session.execute(
        select(MarketerStats).where(
            MarketerStats.marketer_id == marketer_id,
            MarketerStats.date == stats_date,
        )
    )
    stats = result.scalar_one_or_none()
    if not stats:
        stats = MarketerStats(marketer_id=marketer_id, date=stats_date)
        session.add(stats)
        await session.flush()
    return stats


async def _send_marketer_registration_milestone(marketer: Marketer, total_registrations: int) -> bool:
    token = os.getenv("MARKETER_BOT_TOKEN", "").strip()
    if not token or not marketer.telegram_id:
        return False

    bot = get_bot(token)
    try:
        await bot.send_message(
            chat_id=marketer.telegram_id,
            text=(
                "🎉 <b>Registration milestone reached!</b>\n\n"
                f"Your promo campaigns just reached <b>{total_registrations} registrations</b>.\n"
                "Open the dashboard to review the latest performance."
            ),
            parse_mode="HTML",
        )
        return True
    except Exception as exc:
        logger.warning(
            "Failed to send marketer milestone notification to %s: %s",
            marketer.telegram_id,
            exc,
        )
        return False


async def record_marketer_registration(
    session: AsyncSession,
    marketer_id: int,
    mirror_bot_id: int,
    user_id: int,
) -> dict:
    marketer = await session.get(Marketer, marketer_id)
    if not marketer:
        return {"recorded": False, "total_registrations": 0, "milestone_notified": False}

    stats = await get_or_create_marketer_stats_row(session, marketer_id)
    stats.registrations += 1

    await log_marketer_activity(
        session,
        marketer_id,
        "registration",
        details="New referral registration",
        mirror_bot_id=mirror_bot_id,
        user_id=user_id,
    )

    total_registrations = (
        await session.scalar(
            select(func.count(User.id)).where(User.marketer_id == marketer_id)
        )
        or 0
    )

    milestone = total_registrations - (total_registrations % REGISTRATION_MILESTONE_STEP)
    milestone_notified = False
    if (
        milestone >= REGISTRATION_MILESTONE_STEP
        and milestone > int(marketer.last_registration_milestone or 0)
    ):
        milestone_notified = await _send_marketer_registration_milestone(marketer, milestone)
        if milestone_notified:
            marketer.last_registration_milestone = milestone

    # Per-mirror 50-registration milestone: notify owner when mirror hits 50
    registrations_per_mirror = (
        await session.scalar(
            select(func.count(User.id)).where(
                User.marketer_id == marketer_id,
                User.mirror_bot_id == mirror_bot_id,
            )
        )
        or 0
    )
    mirror_milestone = registrations_per_mirror - (registrations_per_mirror % REGISTRATION_MILESTONE_STEP)
    if mirror_milestone >= REGISTRATION_MILESTONE_STEP:
        link = await session.scalar(
            select(MarketerBotLink).where(
                MarketerBotLink.marketer_id == marketer_id,
                MarketerBotLink.mirror_bot_id == mirror_bot_id,
            )
        )
        if link and mirror_milestone > int(getattr(link, "last_registration_milestone", 0) or 0):
            link.last_registration_milestone = mirror_milestone
            await AdminNotificationService.notify_admin_action(
                "MIRROR 50 REGISTRATIONS",
                [
                    f"📢 Mirror <b>#{mirror_bot_id}</b> reached <b>{mirror_milestone} registrations</b>.",
                    f"👤 Marketer ID: <code>{marketer_id}</code>",
                    f"🔗 Mirror ID: <code>{mirror_bot_id}</code>",
                ],
                event_type="mirror_50_registrations",
                urgent=False,
            )

    await session.flush()
    return {
        "recorded": True,
        "total_registrations": total_registrations,
        "milestone_notified": milestone_notified,
    }


async def evaluate_marketer_withdrawal_risk(
    session: AsyncSession,
    marketer_id: int,
) -> list[dict]:
    rows = (
        await session.execute(
            select(
                MarketerActivityLog.mirror_bot_id,
                MarketerActivityLog.user_id,
                func.sum(MarketerActivityLog.amount).label("bonus_total"),
            )
            .where(
                MarketerActivityLog.marketer_id == marketer_id,
                MarketerActivityLog.action == "earning",
                MarketerActivityLog.amount.is_not(None),
                MarketerActivityLog.mirror_bot_id.is_not(None),
                MarketerActivityLog.user_id.is_not(None),
            )
            .group_by(MarketerActivityLog.mirror_bot_id, MarketerActivityLog.user_id)
        )
    ).all()

    if not rows:
        return []

    by_bot: dict[int, dict] = defaultdict(
        lambda: {
            "mirror_bot_id": None,
            "total_bonus": Decimal("0.00"),
            "top_user_id": None,
            "top_user_bonus": Decimal("0.00"),
        }
    )

    for row in rows:
        bot_stats = by_bot[row.mirror_bot_id]
        bot_stats["mirror_bot_id"] = row.mirror_bot_id
        bonus_total = Decimal(row.bonus_total or 0)
        bot_stats["total_bonus"] += bonus_total
        if bonus_total > bot_stats["top_user_bonus"]:
            bot_stats["top_user_bonus"] = bonus_total
            bot_stats["top_user_id"] = row.user_id

    suspicious = []
    for bot_id, bot_stats in by_bot.items():
        total_bonus = bot_stats["total_bonus"]
        if total_bonus <= 0:
            continue
        dominant_share = bot_stats["top_user_bonus"] / total_bonus
        if dominant_share >= AUTO_BLOCK_SHARE_THRESHOLD:
            suspicious.append(
                {
                    "mirror_bot_id": bot_id,
                    "top_user_id": bot_stats["top_user_id"],
                    "top_user_bonus": float(bot_stats["top_user_bonus"]),
                    "total_bonus": float(total_bonus),
                    "share_percent": round(float(dominant_share * Decimal("100")), 2),
                }
            )

    if not suspicious:
        return []

    bot_ids = [item["mirror_bot_id"] for item in suspicious]
    bot_rows = (
        await session.execute(select(MirrorBot.id, MirrorBot.bot_username).where(MirrorBot.id.in_(bot_ids)))
    ).all()
    usernames = {row.id: row.bot_username for row in bot_rows}
    for item in suspicious:
        item["bot_username"] = usernames.get(item["mirror_bot_id"])

    suspicious.sort(key=lambda item: item["share_percent"], reverse=True)
    return suspicious


def build_marketer_withdrawal_block_reason(suspicious_bots: list[dict]) -> str:
    if not suspicious_bots:
        return "Withdrawal blocked by anti-fraud rule."

    parts = []
    for item in suspicious_bots[:3]:
        bot_label = f"@{item['bot_username']}" if item.get("bot_username") else f"bot #{item['mirror_bot_id']}"
        parts.append(
            f"{bot_label}: {item['share_percent']:.2f}% from user {item['top_user_id']}"
        )
    suffix = " | ".join(parts)
    return f"Automatic anti-fraud block: {suffix}"


async def notify_marketer_withdrawal_blocked(
    marketer: Marketer,
    withdrawal: MarketerWithdrawal,
    suspicious_bots: list[dict],
) -> None:
    lines = [
        f"📢 <b>Marketer:</b> {marketer.display_name or marketer.username or marketer.id} (#{marketer.id})",
        f"🆔 <b>Telegram ID:</b> <code>{marketer.telegram_id}</code>",
        f"💵 <b>Withdrawal:</b> #{withdrawal.id} for ${float(withdrawal.amount):.2f}",
        "⛔ <b>Reason:</b> 90%+ of referral bonuses for at least one linked bot came from a single end-user.",
    ]
    for item in suspicious_bots[:5]:
        bot_label = f"@{item['bot_username']}" if item.get("bot_username") else f"bot #{item['mirror_bot_id']}"
        lines.append(
            f"• {bot_label}: {item['share_percent']:.2f}% from user <code>{item['top_user_id']}</code> "
            f"(${item['top_user_bonus']:.2f} of ${item['total_bonus']:.2f})"
        )

    await AdminNotificationService.notify_admin_action(
        "MARKETER WITHDRAWAL BLOCKED",
        lines,
        event_type="marketer_withdrawal_blocked",
        urgent=True,
    )
