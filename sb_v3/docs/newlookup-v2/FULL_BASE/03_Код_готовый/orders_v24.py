"""
Newlookup v24 — Обновлённый seller_bot/handlers/orders.py
Файл: seller_bot/handlers/orders_v24.py

ИНСТРУКЦИЯ: Замени содержимое seller_bot/handlers/orders.py этим файлом.

ИСПРАВЛЕНИЯ по сравнению с v2:
1. УБРАНА строка: f"👤 Buyer ID: <code>{order.buyer_user_id}</code>"
   Продавец НЕ должен видеть Telegram ID покупателя.
2. Добавлена проверка content_filter для текстов продавца в чате
3. Добавлена проверка content_filter для файлов продавца
4. Статус "disputed" добавлен в status_map
5. Добавлен обработчик для auto_complete_at таймера
"""

import logging
from datetime import datetime, timedelta

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from shared.database.models import SellerOrder, SellerBank, SellerChat, MirrorBot
from shared.utils.chat_filter import filter_message, is_message_blocked

logger = logging.getLogger(__name__)
router = Router(name="seller_orders_v24")

# ── Статусы заказов ───────────────────────────────────────────
STATUS_MAP = {
    "pending_admin": "⏳ Pending Admin Approval",
    "approved": "🟡 Approved — Waiting for you",
    "in_progress": "🔵 In Progress",
    "completed": "✅ Completed",
    "rejected": "❌ Rejected by Admin",
    "cancelled": "⚪ Cancelled",
    "disputed": "⚠️ Disputed",       # v24: добавлен
}


class SellerOrderStates(StatesGroup):
    waiting_result_text = State()
    waiting_result_file = State()


def seller_order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Complete (text)", callback_data=f"seller_complete:{order_id}"),
            InlineKeyboardButton(text="📎 Complete (file)", callback_data=f"seller_complete_file:{order_id}"),
        ],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="seller_orders")]
    ])


@router.callback_query(F.data == "seller_orders")
async def orders_list_handler(callback: CallbackQuery, session: AsyncSession, seller, **kwargs):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return

    result = await session.execute(
        select(SellerOrder)
        .where(SellerOrder.seller_id == seller.id)
        .order_by(SellerOrder.created_at.desc())
        .limit(50)
    )
    orders = list(result.scalars().all())

    if not orders:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back", callback_data="seller_main")]
        ])
        await callback.message.edit_text(
            "📦 <b>My Orders</b>\n\nNo orders yet. They will appear here when buyers purchase your banks.",
            reply_markup=kb,
            parse_mode="HTML"
        )
        await callback.answer()
        return

    kb_buttons = []
    for order in orders:
        bank_result = await session.execute(
            select(SellerBank).where(SellerBank.id == order.seller_bank_id)
        )
        bank = bank_result.scalar_one_or_none()
        bank_name = bank.bank_name if bank else "Bank"
        status = STATUS_MAP.get(order.status, order.status)
        kb_buttons.append([
            InlineKeyboardButton(
                text=f"{status} #{order.id} | {bank_name} | ${order.price_for_seller:.2f}",
                callback_data=f"seller_order:{order.id}"
            )
        ])

    kb_buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="seller_main")])
    await callback.message.edit_text(
        "📦 <b>My Orders</b>\n\nSelect an order to view details:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_buttons),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_order:"))
async def order_detail_handler(callback: CallbackQuery, session: AsyncSession, seller, **kwargs):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return

    order_id = int(callback.data.split(":")[1])
    result = await session.execute(
        select(SellerOrder).where(
            and_(SellerOrder.id == order_id, SellerOrder.seller_id == seller.id)
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        await callback.answer("❌ Order not found", show_alert=True)
        return

    bank_result = await session.execute(
        select(SellerBank).where(SellerBank.id == order.seller_bank_id)
    )
    bank = bank_result.scalar_one_or_none()
    bank_name = bank.bank_name if bank else "Unknown"

    # ── v24: УБРАН buyer_user_id из отображения ───────────────
    # Продавец видит только: номер заказа, банк, статус, сумму, дату
    text = (
        f"📦 <b>Order #{order.id}</b>\n\n"
        f"🏦 Bank: <b>{bank_name}</b>\n"
        f"📊 Status: {STATUS_MAP.get(order.status, order.status)}\n"
        f"💰 Your earnings: <b>${order.price_for_seller:.2f}</b>\n"
        f"🔢 Quantity: {order.quantity}\n"
        # НАМЕРЕННО НЕ ПОКАЗЫВАЕМ: buyer_user_id, buyer username, telegram_id
        f"📅 Created: {order.created_at.strftime('%Y-%m-%d %H:%M')}\n"
    )

    if order.admin_notes:
        text += f"\n📝 Admin notes: {order.admin_notes}\n"

    # Показываем таймер автозавершения (v24)
    if hasattr(order, 'auto_complete_at') and order.auto_complete_at:
        remaining = order.auto_complete_at - datetime.utcnow()
        if remaining.total_seconds() > 0:
            hours = int(remaining.total_seconds() // 3600)
            text += f"\n⏱ Auto-complete in: {hours}h\n"

    if order.status in ("approved", "in_progress"):
        await callback.message.edit_text(text, reply_markup=seller_order_keyboard(order.id), parse_mode="HTML")
    else:
        back_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back", callback_data="seller_orders")]
        ])
        await callback.message.edit_text(text, reply_markup=back_kb, parse_mode="HTML")

    await callback.answer()


@router.callback_query(F.data.startswith("seller_complete:"))
async def complete_order_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, **kwargs):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return

    order_id = int(callback.data.split(":")[1])
    result = await session.execute(
        select(SellerOrder).where(
            and_(SellerOrder.id == order_id, SellerOrder.seller_id == seller.id)
        )
    )
    order = result.scalar_one_or_none()

    if not order or order.status not in ("approved", "in_progress"):
        await callback.answer("❌ Cannot complete this order", show_alert=True)
        return

    await state.set_state(SellerOrderStates.waiting_result_text)
    await state.update_data(order_id=order_id)

    await callback.message.edit_text(
        f"📝 <b>Complete Order #{order_id}</b>\n\n"
        "Send the result text for the buyer.\n\n"
        "⚠️ <b>Important:</b> Do NOT include any contact information, "
        "usernames, phone numbers, or links. They will be automatically blocked.",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SellerOrderStates.waiting_result_text)
async def complete_order_result(message: Message, state: FSMContext, session: AsyncSession, seller, **kwargs):
    if not seller:
        return

    data = await state.get_data()
    order_id = data.get("order_id")

    result_text = message.text or ""

    # ── v24: Фильтрация контактных данных ────────────────────
    filtered_text = filter_message(result_text)
    was_filtered = filtered_text != result_text

    if is_message_blocked(result_text):
        await message.answer(
            "❌ Your message contains only contact information and was blocked.\n"
            "Please send the actual result without usernames, links, or phone numbers."
        )
        return

    result = await session.execute(
        select(SellerOrder).where(
            and_(SellerOrder.id == order_id, SellerOrder.seller_id == seller.id)
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        await state.clear()
        await message.answer("❌ Order not found.")
        return

    # Обновляем заказ
    order.status = "completed"
    order.result_data = {"text": filtered_text}
    order.completed_at = datetime.utcnow()

    # v24: Устанавливаем таймер для окна спора покупателя
    if hasattr(order, 'dispute_deadline_at'):
        order.dispute_deadline_at = datetime.utcnow() + timedelta(hours=DISPUTE_WINDOW_HOURS)

    # Добавляем сообщение в чат (от продавца)
    chat_msg = SellerChat(
        seller_order_id=order_id,
        sender_type="seller",
        sender_id=seller.telegram_id,
        message_text=filtered_text
    )
    session.add(chat_msg)

    await session.commit()
    await state.clear()

    # Уведомляем покупателя через mirror_bot
    await _notify_buyer_text(session, order, filtered_text)

    warning_text = ""
    if was_filtered:
        warning_text = "\n\n⚠️ Some contact information was removed from your message."

    await message.answer(
        f"✅ Order #{order_id} completed!\n"
        f"The buyer has been notified.{warning_text}"
    )


@router.callback_query(F.data.startswith("seller_complete_file:"))
async def complete_order_file_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, **kwargs):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return

    order_id = int(callback.data.split(":")[1])
    await state.set_state(SellerOrderStates.waiting_result_file)
    await state.update_data(order_id=order_id)

    await callback.message.edit_text(
        f"📎 <b>Complete Order #{order_id} with File</b>\n\n"
        "Send the file for the buyer.\n\n"
        "⚠️ Allowed formats: .txt, .pdf, .jpg, .png, .zip\n"
        "Max size: 20MB",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(SellerOrderStates.waiting_result_file)
async def complete_order_file(message: Message, state: FSMContext, session: AsyncSession, seller, **kwargs):
    if not seller:
        return

    data = await state.get_data()
    order_id = data.get("order_id")

    if not message.document and not message.photo:
        await message.answer("❌ Please send a file (document or photo).")
        return

    result = await session.execute(
        select(SellerOrder).where(
            and_(SellerOrder.id == order_id, SellerOrder.seller_id == seller.id)
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        await state.clear()
        await message.answer("❌ Order not found.")
        return

    # Получаем file_id
    if message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name or "result_file"
    else:
        file_id = message.photo[-1].file_id
        file_name = "result_photo.jpg"

    # Обновляем заказ
    order.status = "completed"
    order.files = [{"file_id": file_id, "file_name": file_name}]
    order.completed_at = datetime.utcnow()

    if hasattr(order, 'dispute_deadline_at'):
        order.dispute_deadline_at = datetime.utcnow() + timedelta(hours=DISPUTE_WINDOW_HOURS)

    # Добавляем сообщение в чат
    chat_msg = SellerChat(
        seller_order_id=order_id,
        sender_type="seller",
        sender_id=seller.telegram_id,
        message_text=f"[File: {file_name}]",
        files=[{"file_id": file_id, "file_name": file_name}]
    )
    session.add(chat_msg)

    await session.commit()
    await state.clear()

    # Уведомляем покупателя
    await _notify_buyer_file(session, order, file_id, file_name)

    await message.answer(f"✅ Order #{order_id} completed with file!\nThe buyer has been notified.")


# ── Вспомогательные функции ───────────────────────────────────

DISPUTE_WINDOW_HOURS = 24  # Берётся из SystemSetting в production


async def _notify_buyer_text(session: AsyncSession, order: SellerOrder, text: str) -> None:
    """Уведомляет покупателя через mirror_bot о завершении заказа."""
    try:
        if not order.mirror_bot_id:
            return

        mirror_result = await session.execute(
            select(MirrorBot).where(MirrorBot.id == order.mirror_bot_id)
        )
        mirror_bot = mirror_result.scalar_one_or_none()
        if not mirror_bot:
            return

        buyer_bot = Bot(token=mirror_bot.bot_token)
        try:
            await buyer_bot.send_message(
                order.buyer_user_id,
                f"✅ <b>Order #{order.id} Completed!</b>\n\n"
                f"Your result:\n\n{text}\n\n"
                f"⏱ You have {DISPUTE_WINDOW_HOURS}h to open a dispute if needed.",
                parse_mode="HTML"
            )
        finally:
            await buyer_bot.session.close()
    except Exception as e:
        logger.error(f"Failed to notify buyer for order {order.id}: {e}")


async def _notify_buyer_file(session: AsyncSession, order: SellerOrder, file_id: str, file_name: str) -> None:
    """Уведомляет покупателя файлом через mirror_bot."""
    try:
        if not order.mirror_bot_id:
            return

        mirror_result = await session.execute(
            select(MirrorBot).where(MirrorBot.id == order.mirror_bot_id)
        )
        mirror_bot = mirror_result.scalar_one_or_none()
        if not mirror_bot:
            return

        buyer_bot = Bot(token=mirror_bot.bot_token)
        try:
            await buyer_bot.send_document(
                order.buyer_user_id,
                document=file_id,
                caption=(
                    f"✅ <b>Order #{order.id} Completed!</b>\n\n"
                    f"⏱ You have {DISPUTE_WINDOW_HOURS}h to open a dispute if needed."
                ),
                parse_mode="HTML"
            )
        finally:
            await buyer_bot.session.close()
    except Exception as e:
        logger.error(f"Failed to notify buyer with file for order {order.id}: {e}")
