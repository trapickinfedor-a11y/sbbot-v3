"""Лог действий маркетолога — i18n"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import Marketer, MarketerActivityLog
from marketer_bot.constants.language_loader import get_texts

logger = logging.getLogger(__name__)
router = Router(name="marketer_logs")


def _action_labels(t):
    return {
        "registration": t.LOG_REGISTRATION,
        "earning": t.LOG_EARNING,
        "tier_upgrade": t.LOG_TIER_UPGRADE,
        "bot_created": t.LOG_BOT_CREATED,
        "bot_deleted": t.LOG_BOT_DELETED,
    }


async def _render_logs(session: AsyncSession, marketer_id: int, t) -> str:
    logs_result = await session.execute(
        select(MarketerActivityLog)
        .where(MarketerActivityLog.marketer_id == marketer_id)
        .order_by(MarketerActivityLog.created_at.desc())
        .limit(20)
    )
    logs = list(logs_result.scalars().all())

    if not logs:
        return f"{t.LOGS_TITLE}\n\n{t.LOGS_EMPTY}"

    labels = _action_labels(t)
    lines = []
    for entry in logs:
        action = labels.get(entry.action, entry.action)
        amount = f" ${float(entry.amount):.2f}" if entry.amount else ""
        date_str = entry.created_at.strftime("%d.%m %H:%M") if entry.created_at else ""
        details = (entry.details or "")[:60]
        lines.append(f"• {date_str} {action}{amount}\n  {details}")

    return (t.LOGS_TITLE_COUNT.format(n=len(logs)) + "\n\n" + "\n".join(lines))[:4000]


@router.message(Command("logs"))
async def cmd_logs(message: Message, session: AsyncSession, texts=None, **kwargs):
    result = await session.execute(
        select(Marketer).where(Marketer.telegram_id == message.from_user.id)
    )
    marketer = result.scalar_one_or_none()
    t = texts or get_texts(marketer.language if marketer else None)
    if not marketer:
        await message.answer(t.FIRST_START)
        return

    text = await _render_logs(session, marketer.id, t)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t.BTN_BACK, callback_data="marketer_dashboard")],
    ])
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "marketer_logs")
async def logs_callback(callback: CallbackQuery, session: AsyncSession, texts=None, **kwargs):
    result = await session.execute(
        select(Marketer).where(Marketer.telegram_id == callback.from_user.id)
    )
    marketer = result.scalar_one_or_none()
    t = texts or get_texts(marketer.language if marketer else None)
    if not marketer:
        await callback.answer(t.NOT_FOUND, show_alert=True)
        return

    text = await _render_logs(session, marketer.id, t)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t.BTN_BACK, callback_data="marketer_dashboard")],
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()
