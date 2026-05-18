from __future__ import annotations

"""
Чат покупатель ↔ селлер. Один чат на каждого селлера (не на заказ).
"""
import logging
import os
from datetime import datetim, timezone
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from shared.database.models import SellerOrder, SellerChat, SellerBank, Seller, SellerConversation
from shared.services.guarantee_policy_service import is_guarantee_active
from shared.services.seller_conversation_service import get_conversation_from_order
from shared.services.seller_dispute_service import SellerDisputeService
from shared.services.nocodb_service import NocoDBService
from shared.utils.chat_render import get_chat_messages, build_chat_text, buyer_chat_keyboard, CHAT_MSG_LIMIT, BUYER_QUICK_REPLIES
from shared.utils.chat_filter import filter_message, is_message_blocked
from seller_bot.keyboards.inline import _seller_mini_app_url
from mirror_bot.utils.message_utils import safe_edit_message

logger = logging.getLogger(__name__)
router = Router(name="buyer_chat")
BUYER_SENDER_LABELS = {"buyer": "👤 You", "seller": "🏪 Seller", "admin": "👑 Admin"}


class BuyerChatStates(StatesGroup):
    chatting = State()


async def _render_buyer_chat(session, conv_id: int, bank_name: str, offset: int = 0, order_id: int | None = None) -> tuple[str, InlineKeyboardMarkup]:
    messages, total = await get_chat_messages(session, conversation_id=conv_id, offset=offset, limit=CHAT_MSG_LIMIT)
    has_older = total > offset + len(messages)
    older_count = total - offset - len(messages) if has_older else 0
    history_text = build_chat_text(
        messages, BUYER_SENDER_LABELS, parse_mode="Markdown",
        has_older=has_older, older_count=older_count
    )
    can_dispute = False
    if order_id:
        r = await session.execute(select(SellerOrder).where(
            and_(SellerOrder.id == order_id, SellerOrder.buyer_user_id != 0)
        ))
        order = r.scalar_one_or_none()
        can_dispute = bool(
            order
            and order.status == "completed"
            and is_guarantee_active(order.check_expires_at)
        )
    text = f"💬 **Chat with Seller**\n"
    text += f"🏦 {bank_name}\n\n"
    text += history_text if history_text else "_No messages yet. Type your message below._\n\n"
    text += "📝 Type your message:"
    keyboard = buyer_chat_keyboard(conv_id, offset=offset, total=total, can_dispute=can_dispute, order_id=order_id)
    return text, keyboard


async def _add_chat_msg(session, conv_id: int, sender_type: str, sender_id: int, text: str, files=None, order_id=None):
    msg = SellerChat(
        seller_conversation_id=conv_id,
        seller_order_id=order_id,
        sender_type=sender_type,
        sender_id=sender_id,
        message_text=text,
        files=files
    )
    session.add(msg)
    conv = await session.get(SellerConversation, conv_id)
    if conv:
        from datetime import datetim, timezone
        conv.updated_at = datetime.now(timezone.utc)
        NocoDBService.log_seller_buyer_chat(
            order_id=order_id or getattr(conv, "source_order_id", None),
            seller_id=conv.seller_id,
            buyer_id=conv.buyer_user_id,
            message=text,
            files=files,
            extra={
                "sender_type": sender_type,
                "sender_id": sender_id,
                "conversation_id": conv_id,
                "mirror_bot_id": conv.mirror_bot_id,
            },
        )


async def _forward_to_seller(session, conv_id: int, text: str, file_id=None, file_type=None):
    r = await session.execute(select(SellerConversation).where(SellerConversation.id == conv_id))
    conv = r.scalar_one_or_none()
    if not conv:
        return
    seller_r = await session.execute(select(Seller).where(Seller.id == conv.seller_id))
    seller = seller_r.scalar_one_or_none()
    if not seller:
        return
    try:
        from shared.services.bot_pool import get_seller_bot
        s_bot = get_seller_bot()
        if not s_bot:
            return
        keyboard_rows = [
            [InlineKeyboardButton(text="💬 Open in Bot", callback_data=f"seller_chat_conv:{conv_id}")],
        ]
        mini_app_url = _seller_mini_app_url(conv_id)
        if mini_app_url:
            keyboard_rows.append([InlineKeyboardButton(text="🖥 Open Mini App", web_app=WebAppInfo(url=mini_app_url))])
        reply_kb = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
        header = "💬 <b>Buyer wrote about this product</b>\n\n"
        if file_type == "photo" and file_id:
            await s_bot.send_photo(seller.telegram_id, photo=file_id, caption=header + (text or ""), parse_mode="HTML", reply_markup=reply_kb)
        elif file_type == "document" and file_id:
            await s_bot.send_document(seller.telegram_id, document=file_id, caption=header + (text or ""), parse_mode="HTML", reply_markup=reply_kb)
        else:
            await s_bot.send_message(seller.telegram_id, header + (text or ""), parse_mode="HTML", reply_markup=reply_kb)
    except Exception as e:
        logger.error(f"Failed to forward to seller: {e}")


async def _open_chat(callback, session, conv_id: int, order_id: int | None, buyer_id: int, mirror_bot_id: int):
    r = await session.execute(select(SellerConversation).where(
        and_(SellerConversation.id == conv_id, SellerConversation.buyer_user_id == buyer_id)
    ))
    conv = r.scalar_one_or_none()
    if not conv:
        await callback.answer("Not found", show_alert=True)
        return
    bank_name = "Seller"
    if order_id:
        ord_r = await session.execute(select(SellerOrder).where(SellerOrder.id == order_id))
        o = ord_r.scalar_one_or_none()
        if o:
            bank_r = await session.execute(select(SellerBank).where(SellerBank.id == o.seller_bank_id))
            b = bank_r.scalar_one_or_none()
            bank_name = b.bank_name if b else "Seller"
    messages, _ = await get_chat_messages(session, conversation_id=conv_id, offset=0, limit=CHAT_MSG_LIMIT)
    for msg in messages:
        if msg.sender_type == "seller" and not msg.is_read:
            msg.is_read = True
    await session.commit()
    text, keyboard = await _render_buyer_chat(session, conv_id, bank_name, offset=0, order_id=order_id)
    return text, keyboard, conv_id, order_id


@router.callback_query(F.data.startswith("buyer_chat:"))
async def start_buyer_chat_order(callback: CallbackQuery, state: FSMContext, session: AsyncSession, **kwargs):
    """Legacy: buyer_chat:order_id"""
    order_id = int(callback.data.split(":")[1])
    r = await session.execute(select(SellerOrder).where(
        and_(SellerOrder.id == order_id, SellerOrder.buyer_user_id == callback.from_user.id)
    ))
    order = r.scalar_one_or_none()
    if not order:
        await callback.answer("Order not found", show_alert=True)
        return
    conv = await get_conversation_from_order(session, order)
    bank_r = await session.execute(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
    bank = bank_r.scalar_one_or_none()
    bank_name = bank.bank_name if bank else "Seller"
    result = await _open_chat(callback, session, conv.id, order_id, callback.from_user.id, order.mirror_bot_id or 0)
    if result:
        text, keyboard, conv_id, _ = result
        await state.set_state(BuyerChatStates.chatting)
        await state.update_data(chat_conv_id=conv_id, chat_order_id=order_id)
        await safe_edit_message(callback, text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("buyer_chat_conv:"))
async def start_buyer_chat_conv(callback: CallbackQuery, state: FSMContext, session: AsyncSession, **kwargs):
    """buyer_chat_conv:conv_id:order_id (order_id 0 = no order)"""
    parts = callback.data.split(":")
    conv_id = int(parts[1])
    raw_oid = parts[2] if len(parts) > 2 else "0"
    order_id = int(raw_oid) if raw_oid and raw_oid != "0" else None
    result = await _open_chat(callback, session, conv_id, order_id, callback.from_user.id, 0)
    if result:
        text, keyboard, cid, oid = result
        await state.set_state(BuyerChatStates.chatting)
        await state.update_data(chat_conv_id=cid, chat_order_id=oid)
        await safe_edit_message(callback, text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("buyer_chat_load:"))
async def buyer_chat_load_older(callback: CallbackQuery, state: FSMContext, session: AsyncSession, **kwargs):
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Error", show_alert=True)
        return
    conv_id = int(parts[1])
    offset = int(parts[2])
    data = await state.get_data()
    order_id = data.get("chat_order_id")
    r = await session.execute(select(SellerConversation).where(
        and_(SellerConversation.id == conv_id, SellerConversation.buyer_user_id == callback.from_user.id)
    ))
    conv = r.scalar_one_or_none()
    if not conv:
        await callback.answer("Not found", show_alert=True)
        return
    bank_name = "Seller"
    if order_id:
        o_r = await session.execute(select(SellerOrder).where(SellerOrder.id == order_id))
        o = o_r.scalar_one_or_none()
        if o:
            b_r = await session.execute(select(SellerBank).where(SellerBank.id == o.seller_bank_id))
            b = b_r.scalar_one_or_none()
            bank_name = b.bank_name if b else "Seller"
    text, keyboard = await _render_buyer_chat(session, conv_id, bank_name, offset=offset, order_id=order_id)
    await state.set_state(BuyerChatStates.chatting)
    await state.update_data(chat_conv_id=conv_id, chat_order_id=order_id)
    await safe_edit_message(callback, text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.message(BuyerChatStates.chatting, F.text)
async def send_buyer_message(message: Message, state: FSMContext, session: AsyncSession, **kwargs):
    data = await state.get_data()
    conv_id = data.get("chat_conv_id")
    order_id = data.get("chat_order_id")
    if not conv_id:
        await state.clear()
        return
    if message.text and message.text.startswith("/"):
        await state.clear()
        await message.answer("Chat ended.")
        return
    filtered_text = filter_message(message.text)
    if is_message_blocked(message.text):
        await message.answer("⚠️ Сообщение содержит запрещённые данные.", reply_markup=buyer_chat_keyboard(conv_id, 0, 0, order_id=order_id))
        return
    await _add_chat_msg(session, conv_id, "buyer", message.from_user.id, filtered_text, order_id=order_id)
    await session.commit()
    await _forward_to_seller(session, conv_id, filtered_text)
    bank_name = "Seller"
    if order_id:
        o_r = await session.execute(select(SellerOrder).where(SellerOrder.id == order_id))
        o = o_r.scalar_one_or_none()
        if o:
            b_r = await session.execute(select(SellerBank).where(SellerBank.id == o.seller_bank_id))
            b = b_r.scalar_one_or_none()
            bank_name = b.bank_name if b else "Seller"
    text, keyboard = await _render_buyer_chat(session, conv_id, bank_name, offset=0, order_id=order_id)
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(BuyerChatStates.chatting, F.photo)
async def send_buyer_photo(message: Message, state: FSMContext, session: AsyncSession, **kwargs):
    data = await state.get_data()
    conv_id = data.get("chat_conv_id")
    order_id = data.get("chat_order_id")
    if not conv_id:
        await state.clear()
        return
    photo_id = message.photo[-1].file_id
    raw_caption = message.caption or ""
    if raw_caption and is_message_blocked(raw_caption):
        await message.answer("⚠️ Caption contains only blocked contact information.")
        return
    caption = filter_message(raw_caption)
    await _add_chat_msg(session, conv_id, "buyer", message.from_user.id, caption or "[photo]", files=[photo_id], order_id=order_id)
    await session.commit()
    await _forward_to_seller(session, conv_id, caption or "", file_id=photo_id, file_type="photo")
    bank_name = "Seller"
    if order_id:
        o_r = await session.execute(select(SellerOrder).where(SellerOrder.id == order_id))
        o = o_r.scalar_one_or_none()
        if o:
            b_r = await session.execute(select(SellerBank).where(SellerBank.id == o.seller_bank_id))
            b = b_r.scalar_one_or_none()
            bank_name = b.bank_name if b else "Seller"
    text, keyboard = await _render_buyer_chat(session, conv_id, bank_name, offset=0, order_id=order_id)
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


@router.message(BuyerChatStates.chatting, F.document)
async def send_buyer_document(message: Message, state: FSMContext, session: AsyncSession, **kwargs):
    data = await state.get_data()
    conv_id = data.get("chat_conv_id")
    order_id = data.get("chat_order_id")
    if not conv_id:
        await state.clear()
        return
    doc_id = message.document.file_id
    raw_caption = message.caption or ""
    raw_file_name = message.document.file_name or ""
    if raw_caption and is_message_blocked(raw_caption):
        await message.answer("⚠️ Caption contains only blocked contact information.")
        return
    if raw_file_name and filter_message(raw_file_name) != raw_file_name:
        await message.answer("⚠️ File name contains contact information and was blocked.")
        return
    caption = filter_message(raw_caption or raw_file_name)
    await _add_chat_msg(session, conv_id, "buyer", message.from_user.id, caption or "[file]", files=[doc_id], order_id=order_id)
    await session.commit()
    await _forward_to_seller(session, conv_id, caption or "", file_id=doc_id, file_type="document")
    bank_name = "Seller"
    if order_id:
        o_r = await session.execute(select(SellerOrder).where(SellerOrder.id == order_id))
        o = o_r.scalar_one_or_none()
        if o:
            b_r = await session.execute(select(SellerBank).where(SellerBank.id == o.seller_bank_id))
            b = b_r.scalar_one_or_none()
            bank_name = b.bank_name if b else "Seller"
    text, keyboard = await _render_buyer_chat(session, conv_id, bank_name, offset=0, order_id=order_id)
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


@router.callback_query(F.data.startswith("buyer_qr:"))
async def buyer_quick_reply(callback: CallbackQuery, state: FSMContext, session: AsyncSession, **kwargs):
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Error", show_alert=True)
        return
    conv_id = int(parts[1])
    idx = int(parts[2])
    if idx < 0 or idx >= len(BUYER_QUICK_REPLIES):
        await callback.answer("Error", show_alert=True)
        return
    _, msg_text = BUYER_QUICK_REPLIES[idx]
    if is_message_blocked(msg_text):
        await callback.answer("Message contains blocked contact information.", show_alert=True)
        return
    filtered_text = filter_message(msg_text)
    r = await session.execute(select(SellerConversation).where(
        and_(SellerConversation.id == conv_id, SellerConversation.buyer_user_id == callback.from_user.id)
    ))
    conv = r.scalar_one_or_none()
    if not conv:
        await callback.answer("Not found", show_alert=True)
        return
    data = await state.get_data()
    order_id = data.get("chat_order_id")
    await _add_chat_msg(session, conv_id, "buyer", callback.from_user.id, filtered_text, order_id=order_id)
    await session.commit()
    await _forward_to_seller(session, conv_id, filtered_text)
    bank_name = "Seller"
    if order_id:
        o_r = await session.execute(select(SellerOrder).where(SellerOrder.id == order_id))
        o = o_r.scalar_one_or_none()
        if o:
            b_r = await session.execute(select(SellerBank).where(SellerBank.id == o.seller_bank_id))
            b = b_r.scalar_one_or_none()
            bank_name = b.bank_name if b else "Seller"
    text, keyboard = await _render_buyer_chat(session, conv_id, bank_name, offset=0, order_id=order_id)
    await safe_edit_message(callback, text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer("✅ Sent")


@router.callback_query(F.data.startswith("buyer_dispute:"))
async def open_buyer_dispute(callback: CallbackQuery, session: AsyncSession, **kwargs):
    order_id = int(callback.data.split(":")[1])
    r = await session.execute(select(SellerOrder).where(
        and_(SellerOrder.id == order_id, SellerOrder.buyer_user_id == callback.from_user.id)
    ))
    order = r.scalar_one_or_none()
    if not order:
        await callback.answer("Order not found", show_alert=True)
        return
    if order.status != "completed" or not is_guarantee_active(order.check_expires_at):
        await callback.answer("Cannot open dispute for this order.", show_alert=True)
        return
    await SellerDisputeService.open_dispute(
        session,
        order=order,
        opened_by=callback.from_user.id,
        reason="buyer_chat_dispute",
        description="Buyer opened dispute from private seller chat",
        buyer_evidence={
            "source": "buyer_chat",
            "opened_at": datetime.now(timezone.utc).isoformat(),
            "order_id": order.id,
            "buyer_user_id": callback.from_user.id,
            "seller_id": order.seller_id,
            "trigger": "private_chat",
        },
    )
    await session.commit()
    try:
        from shared.services.admin_notification_service import AdminNotificationService
        from shared.services.bot_pool import get_seller_bot
        b_r = await session.execute(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
        bank = b_r.scalar_one_or_none()
        bank_name = bank.bank_name if bank else "Bank"
        await AdminNotificationService.notify_dispute(order_id, bank_name, callback.from_user.id)
        seller_r = await session.execute(select(Seller).where(Seller.id == order.seller_id))
        seller = seller_r.scalar_one_or_none()
        seller_bot = get_seller_bot()
        if seller and seller.telegram_id and seller_bot:
            await seller_bot.send_message(
                seller.telegram_id,
                (
                    "⚠️ <b>Buyer opened a dispute</b>\n\n"
                    f"Order: <b>#{order.id}</b>\n"
                    f"Product: <b>{bank_name}</b>\n"
                    "You have 24 hours to respond in chat before admin escalation."
                ),
                parse_mode="HTML",
            )
    except Exception as e:
        logger.error(f"Failed to notify: {e}")
    await callback.answer("Dispute opened. Admin will review.", show_alert=True)
    conv = await get_conversation_from_order(session, order)
    bank_r = await session.execute(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
    b = bank_r.scalar_one_or_none()
    bank_name = b.bank_name if b else "Seller"
    text, keyboard = await _render_buyer_chat(session, conv.id, bank_name, offset=0, order_id=order_id)
    await safe_edit_message(callback, text, reply_markup=keyboard, parse_mode="Markdown")


@router.callback_query(F.data.startswith("buyer_end_chat:"))
async def end_buyer_chat(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.clear()
    await safe_edit_message(callback, "💬 Chat ended.", parse_mode=None)
    await callback.answer()
