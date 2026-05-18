from __future__ import annotations

"""Support Bot — массовые рассылки по группам (workers, sellers, marketers, all)"""
import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import Worker, Seller, Marketer, User

logger = logging.getLogger(__name__)
router = Router(name="mass_broadcast")

# Only accessible to support/admin staff — checked in handler


class BroadcastFSM(StatesGroup):
    choosing_group = State()
    writing_message = State()
    confirming = State()


GROUP_LABELS = {
    "all_users": "👥 Все пользователи",
    "workers": "👷 Воркеры",
    "sellers": "🏪 Продавцы",
    "marketers": "📢 Маркетологи",
}


def _group_kb():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Все пользователи", callback_data="bc_group:all_users")],
        [InlineKeyboardButton(text="👷 Воркеры", callback_data="bc_group:workers")],
        [InlineKeyboardButton(text="🏪 Продавцы", callback_data="bc_group:sellers")],
        [InlineKeyboardButton(text="📢 Маркетологи", callback_data="bc_group:marketers")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="bc_cancel")],
    ])


def _confirm_kb():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="bc_send"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="bc_cancel"),
        ]
    ])


@router.callback_query(F.data == "mass_broadcast")
async def cb_mass_broadcast_start(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.set_state(BroadcastFSM.choosing_group)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    await callback.message.edit_text(
        "📣 <b>Массовая рассылка</b>\n\nВыберите группу получателей:",
        reply_markup=_group_kb()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bc_group:"))
async def cb_choose_group(callback: CallbackQuery, state: FSMContext, **kwargs):
    group = callback.data.split(":")[1]
    await state.update_data(group=group)
    await state.set_state(BroadcastFSM.writing_message)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    await callback.message.edit_text(
        f"📝 Группа: <b>{GROUP_LABELS[group]}</b>\n\nНапишите текст рассылки:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="bc_cancel")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "bc_cancel")
async def cb_broadcast_cancel(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.clear()
    await callback.message.edit_text("Рассылка отменена.")
    await callback.answer()


@router.message(BroadcastFSM.writing_message)
async def fsm_broadcast_message(message: Message, state: FSMContext, **kwargs):
    await state.update_data(text=message.text or "")
    await state.set_state(BroadcastFSM.confirming)
    data = await state.get_data()
    group_label = GROUP_LABELS.get(data.get("group", ""), "?")
    await message.answer(
        f"📣 <b>Подтверждение рассылки</b>\n\n"
        f"Группа: <b>{group_label}</b>\n\n"
        f"Текст:\n<i>{(message.text or '')[:500]}</i>\n\n"
        f"Отправить?",
        reply_markup=_confirm_kb()
    )


@router.callback_query(F.data == "bc_send", BroadcastFSM.confirming)
async def cb_broadcast_send(callback: CallbackQuery, session: AsyncSession, state: FSMContext, bot: Bot, **kwargs):
    data = await state.get_data()
    await state.clear()
    group = data.get("group", "all_users")
    text = data.get("text", "")

    telegram_ids = await _get_group_ids(session, group)
    if not telegram_ids:
        await callback.message.edit_text("Нет получателей в этой группе.")
        await callback.answer()
        return

    await callback.message.edit_text(
        f"⏳ Отправка рассылки для {len(telegram_ids)} получателей..."
    )

    sent = 0
    failed = 0
    for tid in telegram_ids:
        try:
            await bot.send_message(chat_id=tid, text=text)
            sent += 1
        except Exception as e:
            failed += 1
            logger.warning("Broadcast failed for %s: %s", tid, e)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    await callback.message.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"Отправлено: {sent}\nОшибок: {failed}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu")]
        ])
    )
    await callback.answer()


async def _get_group_ids(session: AsyncSession, group: str) -> list[int]:
    if group == "workers":
        r = await session.execute(
            select(Worker.telegram_id).where(Worker.is_active == True)
        )
        return [row[0] for row in r.fetchall()]
    elif group == "sellers":
        r = await session.execute(
            select(Seller.telegram_id).where(Seller.is_active == True)
        )
        return [row[0] for row in r.fetchall()]
    elif group == "marketers":
        r = await session.execute(
            select(Marketer.telegram_id).where(Marketer.is_active == True)
        )
        return [row[0] for row in r.fetchall()]
    else:  # all_users
        r = await session.execute(
            select(User.user_id).where(User.is_banned == False).limit(5000)
        )
        return [row[0] for row in r.fetchall()]
