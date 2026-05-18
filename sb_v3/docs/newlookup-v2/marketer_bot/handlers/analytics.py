from __future__ import annotations

"""Marketer bot — аналитика с i18n"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import Marketer
from marketer_bot.constants.language_loader import get_texts
from marketer_bot.services.analytics_service import (
    build_analytics_text,
    build_per_bot_text,
    build_trend_text,
)

logger = logging.getLogger(__name__)
router = Router(name="marketer_analytics")


def _period_label(period: str, t) -> str:
    return {"day": t.PERIOD_DAY, "week": t.PERIOD_WEEK, "month": t.PERIOD_MONTH, "all": t.PERIOD_ALL}.get(period, period)


def _analytics_main_kb(current_period: str, t) -> InlineKeyboardMarkup:
    periods = [("day", t.PERIOD_DAY), ("week", t.PERIOD_WEEK), ("month", t.PERIOD_MONTH), ("all", t.PERIOD_ALL)]
    btns = []
    for pid, label in periods:
        if pid == current_period:
            label = f"• {label} •"
        btns.append(InlineKeyboardButton(text=label, callback_data=f"ma_period:{pid}"))

    return InlineKeyboardMarkup(inline_keyboard=[
        btns,
        [
            InlineKeyboardButton(text=t.BTN_BY_BOTS, callback_data="ma_bots"),
            InlineKeyboardButton(text=t.BTN_TRENDS_7, callback_data="ma_trend:7"),
        ],
        [
            InlineKeyboardButton(text=t.BTN_TRENDS_14, callback_data="ma_trend:14"),
            InlineKeyboardButton(text=t.BTN_TRENDS_30, callback_data="ma_trend:30"),
        ],
        [InlineKeyboardButton(text=t.BTN_BACK, callback_data="marketer_dashboard")],
    ])


def _back_kb(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t.BTN_ANALYTICS, callback_data="ma_period:week"),
            InlineKeyboardButton(text=t.BTN_BACK_MAIN, callback_data="marketer_dashboard"),
        ],
    ])


async def _get_marketer(session: AsyncSession, telegram_id: int) -> Marketer | None:
    r = await session.execute(select(Marketer).where(Marketer.telegram_id == telegram_id))
    return r.scalar_one_or_none()


@router.callback_query(F.data == "marketer_analytics")
async def cb_analytics_main(callback: CallbackQuery, session: AsyncSession, texts=None, **kwargs):
    marketer = await _get_marketer(session, callback.from_user.id)
    if not marketer:
        await callback.answer("Not found", show_alert=True)
        return
    t = texts or get_texts(marketer.language)
    text = await build_analytics_text(session, marketer.id, "week", t)
    await callback.message.edit_text(text, reply_markup=_analytics_main_kb("week", t))
    await callback.answer()


@router.callback_query(F.data.startswith("ma_period:"))
async def cb_period(callback: CallbackQuery, session: AsyncSession, texts=None, **kwargs):
    period = callback.data.split(":")[1]
    marketer = await _get_marketer(session, callback.from_user.id)
    if not marketer:
        await callback.answer("Not found", show_alert=True)
        return
    t = texts or get_texts(marketer.language)
    text = await build_analytics_text(session, marketer.id, period, t)
    await callback.message.edit_text(text, reply_markup=_analytics_main_kb(period, t))
    await callback.answer()


@router.callback_query(F.data == "ma_bots")
async def cb_bots_stats(callback: CallbackQuery, session: AsyncSession, texts=None, **kwargs):
    marketer = await _get_marketer(session, callback.from_user.id)
    if not marketer:
        await callback.answer("Not found", show_alert=True)
        return
    t = texts or get_texts(marketer.language)
    text = await build_per_bot_text(session, marketer.id, t)
    await callback.message.edit_text(text, reply_markup=_back_kb(t))
    await callback.answer()


@router.callback_query(F.data.startswith("ma_trend:"))
async def cb_trend(callback: CallbackQuery, session: AsyncSession, texts=None, **kwargs):
    days = int(callback.data.split(":")[1])
    marketer = await _get_marketer(session, callback.from_user.id)
    if not marketer:
        await callback.answer("Not found", show_alert=True)
        return
    t = texts or get_texts(marketer.language)
    text = await build_trend_text(session, marketer.id, days, t)
    await callback.message.edit_text(text, reply_markup=_back_kb(t))
    await callback.answer()
