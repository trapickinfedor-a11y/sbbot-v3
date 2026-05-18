from __future__ import annotations

"""Личный кабинет владельца ботов: статистика, вывод"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from shared.database.session import async_session_maker
from shared.services.bot_owner_service import (
    get_owner_stats,
    get_or_create_owner,
    get_owner_month_topups_chart,
    get_min_withdrawal_amount,
    MIN_WITHDRAWAL,
)
from shared.database.models import BotOwnerWithdrawal, MirrorBot
from shared.services.ledger_projection_service import LedgerProjectionService
from shared.services.ledger_service import LedgerService
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = Router(name="owner_cabinet")


class WithdrawStates(StatesGroup):
    waiting_amount = State()
    waiting_method = State()
    waiting_network = State()
    waiting_requisites = State()


async def _get_owner_keyboard(has_bots: bool):
    kb = []
    if has_bots:
        kb.append([InlineKeyboardButton(text="📊 Моя статистика", callback_data="owner_stats")])
        kb.append([InlineKeyboardButton(text="📈 График месяца", callback_data="owner_month_chart")])
        kb.append([InlineKeyboardButton(text="📜 История выплат", callback_data="owner_withdraw_history")])
        kb.append([InlineKeyboardButton(text="💸 Вывод средств", callback_data="owner_withdraw")])
        kb.append([InlineKeyboardButton(text="➕ Создать ещё бота", callback_data="owner_create_bot")])
    else:
        kb.append([InlineKeyboardButton(text="➕ Создать бота", callback_data="owner_create_bot")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def _build_month_chart_text(chart: dict) -> str:
    max_value = chart["max_value"] or 0
    lines = []
    for label, value in zip(chart["labels"], chart["values"]):
        if max_value > 0 and value > 0:
            bar_len = max(1, round((value / max_value) * 10))
            bar = "█" * bar_len
        else:
            bar = ""
        lines.append(f"{label} | {bar:<10} ${value:,.2f}")

    return (
        f"📈 График пополнений за {chart['month_label']}\n"
        f"Сумма пополнений во всех ваших ботах:\n\n"
        + "\n".join(lines)
        + f"\n\nИтого за месяц: ${chart['total']:,.2f}"
    )


@router.callback_query(F.data == "owner_cabinet")
async def owner_cabinet_callback(callback: CallbackQuery, mirror_service, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id

    async with async_session_maker() as session:
        bots = await mirror_service.get_user_bots(user_id)

        if not bots:
            text = (
                "👋 **Личный кабинет владельца бота**\n\n"
                "У вас пока нет ботов.\n\n"
                "📹 Посмотрите видео и описание, затем нажмите **Создать бота**.\n\n"
                "Ваша комиссия: **10%** с каждого пополнения пользователей."
            )
        else:
            stats = await get_owner_stats(session, user_id)
            bots_text = "\n".join(
                f"• @{bot.bot_username}" for bot in bots if getattr(bot, "bot_username", None)
            ) or "• Боты подключены"
            text = (
                f"📊 **Личный кабинет** ({len(bots)} бот(ов))\n\n"
                f"💰 Баланс: **${stats['balance']:.2f}**\n"
                f"📈 Заработано всего: **${stats['income_total']:.2f}**\n"
                f"💸 Выведено: **${stats['total_withdrawn']:.2f}**\n\n"
                f"**Ваши боты:**\n{bots_text}\n\n"
                f"**За сегодня:**\n"
                f"  Потратили: ${stats['spent_today']:.2f} | Пополнили: ${stats['topped_up_today']:.2f} | Ваш доход: ${stats['income_today']:.2f}\n\n"
                f"**За неделю:**\n"
                f"  Потратили: ${stats['spent_week']:.2f} | Пополнили: ${stats['topped_up_week']:.2f} | Ваш доход: ${stats['income_week']:.2f}\n\n"
                f"**За месяц:**\n"
                f"  Потратили: ${stats['spent_month']:.2f} | Пополнили: ${stats['topped_up_month']:.2f} | Ваш доход: ${stats['income_month']:.2f}\n\n"
                f"Ваша комиссия: **{stats['display_percent']}%** с пополнений"
            )

    await callback.message.edit_text(text, reply_markup=await _get_owner_keyboard(len(bots) > 0))
    await callback.answer()


@router.callback_query(F.data == "owner_stats")
async def owner_stats_callback(callback: CallbackQuery, mirror_service):
    user_id = callback.from_user.id
    async with async_session_maker() as session:
        stats = await get_owner_stats(session, user_id)
        text = (
            f"📊 **Статистика по всем вашим ботам**\n\n"
            f"💰 Баланс: **${stats['balance']:.2f}**\n"
            f"📈 Доход всего: **${stats['income_total']:.2f}**\n\n"
            f"**День:** потратили ${stats['spent_today']:.2f} | пополнили ${stats['topped_up_today']:.2f} | ваш доход ${stats['income_today']:.2f}\n"
            f"**Неделя:** потратили ${stats['spent_week']:.2f} | пополнили ${stats['topped_up_week']:.2f} | ваш доход ${stats['income_week']:.2f}\n"
            f"**Месяц:** потратили ${stats['spent_month']:.2f} | пополнили ${stats['topped_up_month']:.2f} | ваш доход ${stats['income_month']:.2f}"
        )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="owner_cabinet")],
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == "owner_month_chart")
async def owner_month_chart_callback(callback: CallbackQuery, mirror_service):
    user_id = callback.from_user.id
    async with async_session_maker() as session:
        chart = await get_owner_month_topups_chart(session, user_id)
        text = _build_month_chart_text(chart)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="owner_cabinet")],
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode=None)
    await callback.answer()


@router.callback_query(F.data == "owner_withdraw_history")
async def owner_withdraw_history_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with async_session_maker() as session:
        result = await session.execute(
            select(BotOwnerWithdrawal)
            .where(BotOwnerWithdrawal.owner_user_id == user_id)
            .order_by(BotOwnerWithdrawal.created_at.desc())
            .limit(10)
        )
        rows = list(result.scalars().all())

    if not rows:
        text = "📜 История выплат\n\nПока нет заявок."
    else:
        lines = []
        for row in rows:
            network = f" ({row.payment_network})" if row.payment_network else ""
            tx_hash = f"\nHash: {row.tx_hash}" if row.tx_hash else ""
            reject_reason = f"\nПричина: {row.reject_reason}" if row.reject_reason else ""
            lines.append(
                f"• ${float(row.amount):.2f} | {row.payment_method or '-'}{network} | {row.status}"
                f"\n{row.requisites or '-'}{tx_hash}{reject_reason}"
            )
        text = "📜 История выплат\n\n" + "\n\n".join(lines)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="owner_cabinet")],
    ])
    await callback.message.edit_text(text[:4000], reply_markup=kb, parse_mode=None)
    await callback.answer()


@router.callback_query(F.data == "owner_withdraw")
async def owner_withdraw_start(callback: CallbackQuery, mirror_service, state: FSMContext):
    user_id = callback.from_user.id
    async with async_session_maker() as session:
        owner = await get_or_create_owner(session, user_id)
        balance = float((await LedgerProjectionService.get_owner_projection(session, owner.owner_user_id))["balance"])
        min_withdrawal = await get_min_withdrawal_amount(session)

    if balance < min_withdrawal:
        await callback.answer(f"Минимальная сумма вывода: ${min_withdrawal}. Ваш баланс: ${balance:.2f}", show_alert=True)
        return

    await state.set_state(WithdrawStates.waiting_amount)
    await state.update_data(owner_user_id=user_id)
    await callback.message.edit_text(
        f"💸 **Вывод средств**\n\n"
        f"Ваш баланс: **${balance:.2f}**\n"
        f"Минимум: **${min_withdrawal}**\n\n"
        f"Введите сумму для вывода:"
    )
    await callback.answer()


@router.message(WithdrawStates.waiting_amount, F.text)
async def owner_withdraw_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", ".").strip())
    except ValueError:
        await message.answer("Введите число (например 100 или 150.50)")
        return

    data = await state.get_data()
    owner_user_id = data.get("owner_user_id")

    async with async_session_maker() as session:
        owner = await get_or_create_owner(session, owner_user_id)
        balance = float((await LedgerProjectionService.get_owner_projection(session, owner.owner_user_id))["balance"])
        min_withdrawal = await get_min_withdrawal_amount(session)

    if amount < min_withdrawal:
        await message.answer(f"Минимальная сумма: ${min_withdrawal}")
        return
    if amount > balance:
        await message.answer(f"Недостаточно средств. Баланс: ${balance:.2f}")
        return

    await state.update_data(amount=amount)
    await state.set_state(WithdrawStates.waiting_method)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="XMR", callback_data="owner_method:xmr")],
        [InlineKeyboardButton(text="USDT", callback_data="owner_method:usdt")],
        [InlineKeyboardButton(text="BTC", callback_data="owner_method:btc")],
    ])
    await message.answer("Выберите валюту для выплаты:", reply_markup=kb)


@router.callback_query(F.data.startswith("owner_method:"))
async def owner_withdraw_method(callback: CallbackQuery, state: FSMContext):
    payment_method = callback.data.split(":", 1)[1].upper()
    await state.update_data(payment_method=payment_method)
    if payment_method == "USDT":
        await state.set_state(WithdrawStates.waiting_network)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="TRC20", callback_data="owner_network:TRC20")],
            [InlineKeyboardButton(text="ERC20", callback_data="owner_network:ERC20")],
            [InlineKeyboardButton(text="BEP20", callback_data="owner_network:BEP20")],
        ])
        await callback.message.edit_text(
            "Выбрана валюта: USDT\n\nВыберите сеть:",
            reply_markup=kb
        )
    else:
        await state.set_state(WithdrawStates.waiting_requisites)
        await callback.message.edit_text(
            f"Выбрана валюта: {payment_method}\n\n"
            f"Введите реквизиты для выплаты ({payment_method} address / wallet):"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("owner_network:"))
async def owner_withdraw_network(callback: CallbackQuery, state: FSMContext):
    network = callback.data.split(":", 1)[1].upper()
    data = await state.get_data()
    payment_method = data.get("payment_method", "USDT")
    await state.update_data(payment_network=network)
    await state.set_state(WithdrawStates.waiting_requisites)
    await callback.message.edit_text(
        f"Выбрана валюта: {payment_method}\n"
        f"Сеть: {network}\n\n"
        f"Введите реквизиты для выплаты ({payment_method} {network} address):"
    )
    await callback.answer()


@router.message(WithdrawStates.waiting_requisites, F.text)
async def owner_withdraw_requisites(message: Message, state: FSMContext):
    data = await state.get_data()
    owner_user_id = data.get("owner_user_id")
    amount = data.get("amount", 0)
    payment_method = data.get("payment_method")
    payment_network = data.get("payment_network")
    requisites = (message.text or "").strip() or "Не указаны"

    async with async_session_maker() as session:
        owner = await get_or_create_owner(session, owner_user_id)
        balance = float((await LedgerProjectionService.get_owner_projection(session, owner.owner_user_id))["balance"])

        if amount > balance:
            await message.answer("Недостаточно средств. Запрос отменён.")
            await state.clear()
            return

        w = BotOwnerWithdrawal(
            owner_user_id=owner_user_id,
            amount=amount,
            payment_method=payment_method,
            payment_network=payment_network,
            requisites=requisites
        )
        session.add(w)
        await session.flush()
        if not await LedgerService.reserve_owner_withdrawal(
            session,
            owner=owner,
            amount=amount,
            withdrawal_id=w.id,
        ):
            await message.answer("Недостаточно средств. Запрос отменён.")
            await state.clear()
            return
        w.funds_reserved = True
        await session.commit()

    await state.clear()
    network_line = f"Сеть: {payment_network}\n" if payment_network else ""
    await message.answer(
        f"✅ **Заявка на вывод создана!**\n\n"
        f"Сумма: ${amount:.2f}\n"
        f"Валюта: {payment_method}\n"
        f"{network_line}"
        f"Реквизиты: {requisites[:50]}...\n\n"
        f"Ожидайте подтверждения. Вы получите уведомление."
    )

    # Уведомление админам о новой заявке
    import os
    admin_ids = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
    for admin_id in admin_ids:
        try:
            admin_network_line = f"🌐 Сеть: {payment_network}\n" if payment_network else ""
            await message.bot.send_message(
                admin_id,
                f"💸 **Новая заявка на вывод (владелец бота)**\n\n"
                f"👤 ID: {owner_user_id}\n"
                f"💰 Сумма: ${amount:.2f}\n"
                f"🪙 Валюта: {payment_method}\n"
                f"{admin_network_line}"
                f"📋 Реквизиты: {requisites}\n\n"
                f"Обработайте в админ-панели: /marketers или веб-панель",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

@router.callback_query(F.data == "owner_create_bot")
async def owner_create_bot_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = (
        "➕ **Создать бота**\n\n"
        "1️⃣ Откройте [@BotFather](https://t.me/BotFather) → отправьте `/newbot`\n"
        "2️⃣ Придумайте имя и username (должен заканчиваться на *bot*)\n"
        "3️⃣ Скопируйте токен и отправьте его сюда\n\n"
        "Ваша комиссия: **10%** с каждого пополнения пользователей."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="owner_cabinet")],
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()
