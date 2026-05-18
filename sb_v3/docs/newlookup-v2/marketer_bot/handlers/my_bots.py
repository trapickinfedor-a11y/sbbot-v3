from __future__ import annotations

"""Marketer bot — управление ботами (до 10 штук), i18n"""
import logging
import os
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import Marketer, MarketerOwnBot, MirrorBot
from marketer_bot.constants.language_loader import get_texts
from marketer_bot.services.marketer_service import (
    get_marketer_bots,
    get_total_users_across_bots,
    get_tier,
    get_next_tier,
)

logger = logging.getLogger(__name__)
router = Router(name="marketer_my_bots")

MAX_BOTS_PER_MARKETER = 10
MAIN_BOT_API = os.getenv("MAIN_BOT_API_URL_INTERNAL", "http://main_bot:8080")


async def _notify_main_bot_start(bot_id):
    if not bot_id:
        return
    try:
        import httpx
        from shared.security.internal_api import build_internal_api_headers
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{MAIN_BOT_API}/bot/toggle",
                json={"bot_id": bot_id, "is_active": True},
                headers=build_internal_api_headers(),
            )
    except Exception as e:
        logger.warning("Failed to notify main_bot to start mirror bot %s: %s", bot_id, e)


async def _notify_main_bot_stop(bot_id):
    if not bot_id:
        return
    try:
        import httpx
        from shared.security.internal_api import build_internal_api_headers
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{MAIN_BOT_API}/bot/toggle",
                json={"bot_id": bot_id, "is_active": False},
                headers=build_internal_api_headers(),
            )
    except Exception as e:
        logger.warning("Failed to notify main_bot to stop mirror bot %s: %s", bot_id, e)


class CreateBotFSM(StatesGroup):
    waiting_token = State()


class EditBotFSM(StatesGroup):
    waiting_welcome = State()


def _bots_list_kb(bots: list[MarketerOwnBot], t) -> InlineKeyboardMarkup:
    rows = []
    for bot in bots:
        status = "✅" if bot.is_active else "❌"
        label = f"{status} @{bot.bot_username or '?'} — {bot.total_users} {t.USERS_SHORT}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"mbot_detail:{bot.id}")])
    if len(bots) < MAX_BOTS_PER_MARKETER:
        rows.append([InlineKeyboardButton(text=t.BTN_CREATE_BOT, callback_data="mbot_create")])
    rows.append([InlineKeyboardButton(text=t.BTN_BACK, callback_data="marketer_dashboard")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _bot_detail_kb(bot: MarketerOwnBot, t) -> InlineKeyboardMarkup:
    toggle = t.BTN_TOGGLE_OFF if bot.is_active else t.BTN_TOGGLE_ON
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t.BTN_EDIT_WELCOME, callback_data=f"mbot_edit_welcome:{bot.id}")],
        [InlineKeyboardButton(text=toggle, callback_data=f"mbot_toggle:{bot.id}")],
        [InlineKeyboardButton(text=t.BTN_DELETE, callback_data=f"mbot_delete:{bot.id}")],
        [InlineKeyboardButton(text=t.BTN_BACK_BOTS, callback_data="mbot_list")],
    ])


def _cancel_kb(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t.BTN_CANCEL, callback_data="mbot_list")]
    ])


async def _get_marketer(session: AsyncSession, telegram_id: int) -> Marketer | None:
    r = await session.execute(select(Marketer).where(Marketer.telegram_id == telegram_id))
    return r.scalar_one_or_none()


def _bot_stats_text(bot: MarketerOwnBot, tier_percent: int, t) -> str:
    status = t.BOT_ACTIVE if bot.is_active else t.BOT_INACTIVE
    welcome = bot.welcome_message or t.BOT_WELCOME_DEFAULT
    return (
        f"🤖 <b>@{bot.bot_username or '?'}</b>\n"
        f"{status}\n\n"
        f"{t.BOT_USERS}: <b>{bot.total_users}</b>\n"
        f"{t.BOT_ORDERS}: <b>{bot.total_orders}</b>\n"
        f"{t.BOT_EARNED}: <b>${float(bot.total_earned):.2f}</b>\n"
        f"{t.BOT_RATE}: <b>{tier_percent}%</b>\n\n"
        f"{t.BOT_WELCOME}:\n<i>{welcome}</i>"
    )


@router.message(Command("bots"))
async def cmd_bots(message: Message, session: AsyncSession, texts=None, **kwargs):
    marketer = await _get_marketer(session, message.from_user.id)
    if not marketer:
        t = texts or get_texts()
        await message.answer(t.FIRST_START)
        return
    t = texts or get_texts(marketer.language)
    await _show_bots_list(message, session, marketer, t)


@router.callback_query(F.data == "mbot_list")
async def cb_bots_list(callback: CallbackQuery, session: AsyncSession, state: FSMContext, texts=None, **kwargs):
    await state.clear()
    marketer = await _get_marketer(session, callback.from_user.id)
    if not marketer:
        await callback.answer("Not found", show_alert=True)
        return
    t = texts or get_texts(marketer.language)
    await _show_bots_list(callback.message, session, marketer, t, edit=True)
    await callback.answer()


async def _show_bots_list(message, session, marketer, t, edit=False):
    bots = await get_marketer_bots(session, marketer.id)
    total_users = await get_total_users_across_bots(session, marketer.id)
    tier = get_tier(total_users)
    next_t = get_next_tier(total_users)

    text = (
        f"{t.MY_BOTS_TITLE}  ({len(bots)}/{MAX_BOTS_PER_MARKETER})\n"
        f"{tier['icon']} {t.TIER_LEVEL}: <b>{tier['name']}</b> — {tier['display_percent']}%\n"
        f"{t.TOTAL_USERS}: <b>{total_users}</b>\n"
    )
    if next_t:
        left = next_t["min_users"] - total_users
        text += t.TIER_UNTIL.format(percent=next_t["display_percent"], left=left) + "\n"
    text += "\n"

    if not bots:
        text += t.NO_BOTS_YET
    else:
        for b in bots:
            status = "✅" if b.is_active else "❌"
            text += f"{status} @{b.bot_username or '?'} — {b.total_users} {t.USERS_SHORT}, ${float(b.total_earned):.2f}\n"

    kb = _bots_list_kb(bots, t)
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "mbot_create")
async def cb_create_bot_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext, texts=None, **kwargs):
    marketer = await _get_marketer(session, callback.from_user.id)
    if not marketer:
        await callback.answer("Not found", show_alert=True)
        return
    t = texts or get_texts(marketer.language)
    bots = await get_marketer_bots(session, marketer.id)
    if len(bots) >= MAX_BOTS_PER_MARKETER:
        await callback.answer(t.BOT_LIMIT.format(max=MAX_BOTS_PER_MARKETER), show_alert=True)
        return

    await state.set_state(CreateBotFSM.waiting_token)
    await callback.message.edit_text(
        f"{t.CREATE_BOT_TITLE}\n\n{t.CREATE_STEP1}",
        reply_markup=_cancel_kb(t),
    )
    await callback.answer()


@router.message(CreateBotFSM.waiting_token)
async def fsm_create_token(message: Message, session: AsyncSession, state: FSMContext, texts=None, **kwargs):
    marketer = await _get_marketer(session, message.from_user.id)
    if not marketer:
        await state.clear()
        return
    t = texts or get_texts(marketer.language if marketer else None)
    token = message.text.strip() if message.text else ""
    if not token or ":" not in token or len(token) < 40:
        await message.answer(t.CREATE_BAD_TOKEN, reply_markup=_cancel_kb(t))
        return

    exists = await session.execute(
        select(MarketerOwnBot).where(MarketerOwnBot.bot_token == token)
    )
    if exists.scalar_one_or_none():
        await message.answer(t.CREATE_DUPLICATE, reply_markup=_cancel_kb(t))
        return

    try:
        test_bot = Bot(token=token)
        bot_info = await test_bot.get_me()
        await test_bot.session.close()
        bot_username = bot_info.username
        bot_name = bot_info.full_name
    except Exception:
        await message.answer(t.CREATE_INVALID, reply_markup=_cancel_kb(t))
        return

    bot_obj = MarketerOwnBot(
        marketer_id=marketer.id,
        bot_token=token,
        bot_username=bot_username,
        bot_name=bot_name,
        welcome_message=None,
        is_active=True,
        is_verified=True,
    )
    session.add(bot_obj)

    existing_mirror = await session.execute(
        select(MirrorBot).where(MirrorBot.bot_token == token)
    )
    mirror = existing_mirror.scalar_one_or_none()
    if mirror:
        mirror.is_active = True
        mirror.bot_type = "marketer"
    else:
        from datetime import datetime, timezone
        mirror = MirrorBot(
            bot_token=token,
            bot_username=bot_username,
            owner_user_id=marketer.telegram_id,
            bot_type="marketer",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        session.add(mirror)

    await session.commit()
    await session.refresh(bot_obj)
    await session.refresh(mirror)
    await state.clear()

    await _notify_main_bot_start(mirror.id)

    total_users = await get_total_users_across_bots(session, marketer.id)
    tier = get_tier(total_users)

    await message.answer(
        t.CREATE_FOUND.format(username=bot_username) + "\n\n" +
        t.BOT_CREATED.format(
            username=bot_username,
            icon=tier["icon"], tier=tier["name"],
            percent=tier["display_percent"], total=total_users,
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t.BTN_BACK_BOTS, callback_data="mbot_list")],
        ]),
    )


@router.callback_query(F.data.startswith("mbot_detail:"))
async def cb_bot_detail(callback: CallbackQuery, session: AsyncSession, texts=None, **kwargs):
    bot_id = int(callback.data.split(":")[1])
    r = await session.execute(select(MarketerOwnBot).where(MarketerOwnBot.id == bot_id))
    bot = r.scalar_one_or_none()
    marketer = await _get_marketer(session, callback.from_user.id)
    t = texts or get_texts(marketer.language if marketer else None)
    if not bot:
        await callback.answer(t.NOT_FOUND, show_alert=True)
        return
    total_users = await get_total_users_across_bots(session, marketer.id) if marketer else 0
    tier = get_tier(total_users)
    await callback.message.edit_text(
        _bot_stats_text(bot, tier["display_percent"], t),
        reply_markup=_bot_detail_kb(bot, t),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("mbot_toggle:"))
async def cb_bot_toggle(callback: CallbackQuery, session: AsyncSession, texts=None, **kwargs):
    bot_id = int(callback.data.split(":")[1])
    r = await session.execute(select(MarketerOwnBot).where(MarketerOwnBot.id == bot_id))
    bot = r.scalar_one_or_none()
    marketer = await _get_marketer(session, callback.from_user.id)
    t = texts or get_texts(marketer.language if marketer else None)
    if not bot:
        await callback.answer(t.NOT_FOUND, show_alert=True)
        return
    bot.is_active = not bot.is_active

    mr = await session.execute(select(MirrorBot).where(MirrorBot.bot_token == bot.bot_token))
    mirror = mr.scalar_one_or_none()
    if mirror:
        mirror.is_active = bot.is_active
    await session.commit()

    if mirror:
        if bot.is_active:
            await _notify_main_bot_start(mirror.id)
        else:
            await _notify_main_bot_stop(mirror.id)

    status = t.BOT_ACTIVATED if bot.is_active else t.BOT_DEACTIVATED
    await callback.answer(status, show_alert=True)
    total_users = await get_total_users_across_bots(session, marketer.id) if marketer else 0
    tier = get_tier(total_users)
    await callback.message.edit_text(
        _bot_stats_text(bot, tier["display_percent"], t),
        reply_markup=_bot_detail_kb(bot, t),
    )


@router.callback_query(F.data.startswith("mbot_delete:"))
async def cb_bot_delete(callback: CallbackQuery, session: AsyncSession, texts=None, **kwargs):
    bot_id = int(callback.data.split(":")[1])
    r = await session.execute(select(MarketerOwnBot).where(MarketerOwnBot.id == bot_id))
    bot = r.scalar_one_or_none()
    marketer = await _get_marketer(session, callback.from_user.id)
    t = texts or get_texts(marketer.language if marketer else None)
    if not bot:
        await callback.answer(t.NOT_FOUND, show_alert=True)
        return

    mr = await session.execute(select(MirrorBot).where(MirrorBot.bot_token == bot.bot_token))
    mirror = mr.scalar_one_or_none()
    mirror_id = mirror.id if mirror else None
    if mirror:
        mirror.is_active = False

    await session.delete(bot)
    await session.commit()

    if mirror_id:
        await _notify_main_bot_stop(mirror_id)

    await callback.answer(t.BOT_DELETED, show_alert=True)
    if marketer:
        await _show_bots_list(callback.message, session, marketer, t, edit=True)


@router.callback_query(F.data.startswith("mbot_edit_welcome:"))
async def cb_edit_welcome_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession, texts=None, **kwargs):
    marketer = await _get_marketer(session, callback.from_user.id)
    t = texts or get_texts(marketer.language if marketer else None)
    bot_id = int(callback.data.split(":")[1])
    await state.set_state(EditBotFSM.waiting_welcome)
    await state.update_data(bot_id=bot_id)
    await callback.message.edit_text(t.ENTER_WELCOME, reply_markup=_cancel_kb(t))
    await callback.answer()


@router.message(EditBotFSM.waiting_welcome)
async def fsm_edit_welcome(message: Message, session: AsyncSession, state: FSMContext, texts=None, **kwargs):
    marketer = await _get_marketer(session, message.from_user.id)
    t = texts or get_texts(marketer.language if marketer else None)
    data = await state.get_data()
    bot_id = data.get("bot_id")
    r = await session.execute(select(MarketerOwnBot).where(MarketerOwnBot.id == bot_id))
    bot = r.scalar_one_or_none()
    if not bot:
        await state.clear()
        return
    bot.welcome_message = (message.text or "").strip()
    await session.commit()
    await state.clear()
    await message.answer(
        t.WELCOME_UPDATED,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t.BTN_BACK_BOTS, callback_data="mbot_list")],
        ]),
    )
