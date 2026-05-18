from __future__ import annotations

"""
Чат селлер ↔ покупатель. Один чат на каждого покупателя (не на заказ).
"""
import logging
import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from shared.database.models import SellerOrder, SellerChat, SellerBank, MirrorBot, SellerConversation
from shared.services.seller_conversation_service import get_conversation_from_order, get_or_create_conversation
from shared.services.seller_dispute_service import SellerDisputeService
from shared.services.nocodb_service import NocoDBService
from shared.utils.chat_render import get_chat_messages, build_chat_text, seller_chat_keyboard, CHAT_MSG_LIMIT, SELLER_QUICK_REPLIES
from shared.utils.chat_filter import filter_message, is_message_blocked
from seller_bot.keyboards.inline import _seller_mini_app_url, seller_order_keyboard
from seller_bot.utils import get_seller_unread_count

logger = logging.getLogger(__name__)
router = Router(name="seller_chat")
SELLER_SENDER_LABELS = {"buyer": "👤 Buyer", "seller": "🏪 You", "admin": "👑 Admin"}


def _short_product_name(name: str | None, limit: int = 22) -> str:
    if not name:
        return "Product"
    clean = " ".join(name.split())
    return clean if len(clean) <= limit else clean[: limit - 1] + "…"


async def _get_conv_button_label(session: AsyncSession, conv: SellerConversation) -> str:
    latest_order_result = await session.execute(
        select(SellerOrder)
        .where(
            and_(
                SellerOrder.seller_id == conv.seller_id,
                SellerOrder.buyer_user_id == conv.buyer_user_id,
                SellerOrder.mirror_bot_id == conv.mirror_bot_id,
            )
        )
        .order_by(SellerOrder.created_at.desc())
        .limit(1)
    )
    latest_order = latest_order_result.scalar_one_or_none()
    if latest_order:
        bank = await session.scalar(select(SellerBank).where(SellerBank.id == latest_order.seller_bank_id))
        product_name = _short_product_name(bank.bank_name) if bank and bank.bank_name else "Product"
        return f"Order #{latest_order.id} | {product_name}"
    return "Buyer chat"


class SellerChatStates(StatesGroup):
    chatting = State()


async def _render_seller_chat(session, conv_id: int, offset: int = 0) -> tuple[str, InlineKeyboardMarkup]:
    messages, total = await get_chat_messages(session, conversation_id=conv_id, offset=offset, limit=CHAT_MSG_LIMIT)
    has_older = total > offset + len(messages)
    older_count = total - offset - len(messages) if has_older else 0
    history_text = build_chat_text(
        messages, SELLER_SENDER_LABELS, parse_mode="HTML",
        has_older=has_older, older_count=older_count
    )
    
    # Get conversation to find related order
    conv = await session.get(SellerConversation, conv_id)
    order_info = ""
    if conv:
        # Try to find the latest order for this conversation
        latest_order_result = await session.execute(
            select(SellerOrder)
            .where(
                and_(
                    SellerOrder.seller_id == conv.seller_id,
                    SellerOrder.buyer_user_id == conv.buyer_user_id,
                    SellerOrder.mirror_bot_id == conv.mirror_bot_id,
                )
            )
            .order_by(SellerOrder.created_at.desc())
            .limit(1)
        )
        latest_order = latest_order_result.scalar_one_or_none()
        if latest_order:
            order_info = f" | Order #{latest_order.id}"
    
    text = f"💬 <b>Buyer Chat{order_info}</b>\n\n"
    text += history_text if history_text else "<i>No messages yet. Send a message to the buyer.</i>\n\n"
    text += "📝 Type your message below or press End Chat:"
    keyboard = seller_chat_keyboard(conv_id, offset=offset, total=total)
    return text, keyboard


async def _resolve_conv_from_callback(session, callback_data: str, seller_id: int):
    """callback_data: seller_chat:order_id или seller_chat_conv:conv_id"""
    parts = callback_data.split(":")
    if len(parts) < 2:
        return None, None
    if parts[0] == "seller_chat_conv":
        conv_id = int(parts[1])
        r = await session.execute(select(SellerConversation).where(
            and_(SellerConversation.id == conv_id, SellerConversation.seller_id == seller_id)
        ))
        conv = r.scalar_one_or_none()
        return conv, None
    order_id = int(parts[1])
    r = await session.execute(select(SellerOrder).where(
        and_(SellerOrder.id == order_id, SellerOrder.seller_id == seller_id)
    ))
    order = r.scalar_one_or_none()
    if not order:
        return None, None
    conv = await get_conversation_from_order(session, order)
    return conv, order


@router.callback_query(F.data.startswith("seller_chat:") | F.data.startswith("seller_chat_conv:"))
async def start_chat_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    if not seller or not seller_actor or not seller_actor.can_support():
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    conv, order = await _resolve_conv_from_callback(session, callback.data, seller.id)
    if not conv:
        await callback.answer("❌ Not found", show_alert=True)
        return
    if seller_actor.is_helper and seller_actor.role == "support_helper" and conv.assigned_helper_id not in (None, seller_actor.helper.id):
        await callback.answer("❌ Chat is assigned to another helper", show_alert=True)
        return
    if seller_actor.is_helper and conv.assigned_helper_id is None:
        from datetime import datetime, timezone
        conv.assigned_helper_id = seller_actor.helper.id
        conv.assigned_at = datetime.now(timezone.utc)
        conv.assigned_by = seller_actor.actor_telegram_id
    messages, _ = await get_chat_messages(session, conversation_id=conv.id, offset=0, limit=CHAT_MSG_LIMIT)
    for msg in messages:
        if msg.sender_type == "buyer" and not msg.is_read:
            msg.is_read = True
    await session.commit()
    text, keyboard = await _render_seller_chat(session, conv.id, offset=0)
    await state.set_state(SellerChatStates.chatting)
    await state.update_data(chat_conv_id=conv.id, chat_mirror_bot_id=conv.mirror_bot_id)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("seller_chat_load:"))
async def seller_chat_load_older(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    if not seller or not seller_actor or not seller_actor.can_support():
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Error", show_alert=True)
        return
    conv_id = int(parts[1])
    offset = int(parts[2])
    r = await session.execute(select(SellerConversation).where(
        and_(SellerConversation.id == conv_id, SellerConversation.seller_id == seller.id)
    ))
    conv = r.scalar_one_or_none()
    if not conv:
        await callback.answer("❌ Not found", show_alert=True)
        return
    if seller_actor.is_helper and seller_actor.role == "support_helper" and conv.assigned_helper_id not in (None, seller_actor.helper.id):
        await callback.answer("❌ Chat is assigned to another helper", show_alert=True)
        return
    text, keyboard = await _render_seller_chat(session, conv.id, offset=offset)
    await state.set_state(SellerChatStates.chatting)
    await state.update_data(chat_conv_id=conv.id, chat_mirror_bot_id=conv.mirror_bot_id)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


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
        from datetime import datetime, timezone
        conv.updated_at = datetime.now(timezone.utc)
        if sender_type == "seller" and order_id:
            await SellerDisputeService.mark_seller_responded(
                session,
                order_id=order_id,
                message_text=text,
                files=files,
            )
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


async def _forward_to_buyer(session, conv: SellerConversation, text: str, file_id=None, file_type=None):
    if not conv.mirror_bot_id:
        return
    try:
        from shared.services.bot_pool import get_mirror_bot_instance
        from shared.database.models import MirrorBot
        r = await session.execute(select(MirrorBot).where(MirrorBot.id == conv.mirror_bot_id))
        mb = r.scalar_one_or_none()
        if not mb:
            return
        buyer_bot = get_mirror_bot_instance(mb.bot_token)
        header = f"💬 <b>Message from Seller</b>\n\n"
        if file_type == "photo" and file_id:
            await buyer_bot.send_photo(conv.buyer_user_id, photo=file_id, caption=header + (text or ""), parse_mode="HTML")
        elif file_type == "document" and file_id:
            await buyer_bot.send_document(conv.buyer_user_id, document=file_id, caption=header + (text or ""), parse_mode="HTML")
        else:
            await buyer_bot.send_message(conv.buyer_user_id, header + (text or ""), parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to forward to buyer: {e}")


@router.message(SellerChatStates.chatting, Command("cancel"))
async def chat_cancel(message: Message, state: FSMContext, **kwargs):
    await state.clear()
    await message.answer("Chat ended.")


@router.message(SellerChatStates.chatting, F.text)
async def send_chat_message(message: Message, state: FSMContext, session: AsyncSession, seller, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    if not seller_actor or not seller_actor.can_support():
        await state.clear()
        await message.answer("❌ Not authorized")
        return
    data = await state.get_data()
    conv_id = data.get("chat_conv_id")
    if not conv_id:
        await state.clear()
        await message.answer("❌ Chat session expired.")
        return
    filtered_text = filter_message(message.text)
    if is_message_blocked(message.text):
        await message.answer("⚠️ Сообщение содержит запрещённые данные (ссылки, контакты).", reply_markup=seller_chat_keyboard(conv_id, 0, 0), parse_mode="HTML")
        return
    await _add_chat_msg(session, conv_id, "seller", seller_actor.actor_telegram_id, filtered_text)
    await session.commit()
    r = await session.execute(select(SellerConversation).where(SellerConversation.id == conv_id))
    conv = r.scalar_one_or_none()
    if conv:
        await _forward_to_buyer(session, conv, filtered_text)
    text, keyboard = await _render_seller_chat(session, conv_id, offset=0)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(SellerChatStates.chatting, F.photo)
async def send_chat_photo(message: Message, state: FSMContext, session: AsyncSession, seller, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    if not seller_actor or not seller_actor.can_support():
        await state.clear()
        await message.answer("❌ Not authorized")
        return
    data = await state.get_data()
    conv_id = data.get("chat_conv_id")
    if not conv_id:
        await state.clear()
        return
    photo_id = message.photo[-1].file_id
    raw_caption = message.caption or ""
    if raw_caption and is_message_blocked(raw_caption):
        await message.answer("⚠️ Caption contains only blocked contact information.", reply_markup=seller_chat_keyboard(conv_id, 0, 0), parse_mode="HTML")
        return
    caption = filter_message(raw_caption)
    await _add_chat_msg(session, conv_id, "seller", seller_actor.actor_telegram_id, caption or "[photo]", files=[photo_id])
    await session.commit()
    conv = await session.scalar(select(SellerConversation).where(SellerConversation.id == conv_id))
    if conv:
        await _forward_to_buyer(session, conv, caption or "", file_id=photo_id, file_type="photo")
    text, keyboard = await _render_seller_chat(session, conv_id, offset=0)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.message(SellerChatStates.chatting, F.document)
async def send_chat_document(message: Message, state: FSMContext, session: AsyncSession, seller, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    if not seller_actor or not seller_actor.can_support():
        await state.clear()
        await message.answer("❌ Not authorized")
        return
    data = await state.get_data()
    conv_id = data.get("chat_conv_id")
    if not conv_id:
        await state.clear()
        return
    doc_id = message.document.file_id
    raw_caption = message.caption or ""
    raw_file_name = message.document.file_name or ""
    if raw_caption and is_message_blocked(raw_caption):
        await message.answer("⚠️ File caption contains only blocked contact information.", reply_markup=seller_chat_keyboard(conv_id, 0, 0), parse_mode="HTML")
        return
    if raw_file_name and filter_message(raw_file_name) != raw_file_name:
        await message.answer("⚠️ File name contains contact information and was blocked.", reply_markup=seller_chat_keyboard(conv_id, 0, 0), parse_mode="HTML")
        return
    caption = filter_message(raw_caption or raw_file_name)
    await _add_chat_msg(session, conv_id, "seller", seller_actor.actor_telegram_id, caption or "[file]", files=[doc_id])
    await session.commit()
    r = await session.execute(select(SellerConversation).where(SellerConversation.id == conv_id))
    conv = r.scalar_one_or_none()
    if conv:
        await _forward_to_buyer(session, conv, caption or "", file_id=doc_id, file_type="document")
    text, keyboard = await _render_seller_chat(session, conv_id, offset=0)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("seller_qr:"))
async def quick_reply_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    if not seller or not seller_actor or not seller_actor.can_support():
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Error", show_alert=True)
        return
    conv_id = int(parts[1])
    idx = int(parts[2])
    if idx < 0 or idx >= len(SELLER_QUICK_REPLIES):
        await callback.answer("Error", show_alert=True)
        return
    _, msg_text = SELLER_QUICK_REPLIES[idx]
    if is_message_blocked(msg_text):
        await callback.answer("⚠️ Message contains blocked contact information.", show_alert=True)
        return
    filtered_text = filter_message(msg_text)
    r = await session.execute(select(SellerConversation).where(
        and_(SellerConversation.id == conv_id, SellerConversation.seller_id == seller.id)
    ))
    conv = r.scalar_one_or_none()
    if not conv:
        await callback.answer("❌ Not found", show_alert=True)
        return
    if seller_actor.is_helper and seller_actor.role == "support_helper" and conv.assigned_helper_id not in (None, seller_actor.helper.id):
        await callback.answer("❌ Chat is assigned to another helper", show_alert=True)
        return
    await _add_chat_msg(session, conv_id, "seller", seller_actor.actor_telegram_id, filtered_text)
    await session.commit()
    await _forward_to_buyer(session, conv, filtered_text)
    text, keyboard = await _render_seller_chat(session, conv_id, offset=0)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer("✅ Sent")


@router.callback_query(F.data.startswith("seller_end_chat:"))
async def end_chat_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, **kwargs):
    await state.clear()
    conv_id = int(callback.data.split(":")[1])
    from seller_bot.keyboards.inline import seller_main_menu
    unread = await get_seller_unread_count(session, seller.id)
    seller_actor = kwargs.get("seller_actor")
    await callback.message.edit_text(
        "Chat ended.",
        reply_markup=seller_main_menu(unread_count=unread, actor_role=seller_actor.role if seller_actor else None),
    )
    await callback.answer()


@router.callback_query(F.data == "seller_messages")
async def messages_overview(callback: CallbackQuery, session: AsyncSession, seller, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    if not seller or not seller_actor or not seller_actor.can_support():
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    # Список чатов (покупателей) с непрочитанными — по conversation
    unread_result = await session.execute(
        select(
            SellerChat.seller_conversation_id,
            func.count(SellerChat.id).label("unread_count")
        ).join(SellerConversation, SellerChat.seller_conversation_id == SellerConversation.id).where(
            and_(
                SellerConversation.seller_id == seller.id,
                SellerChat.sender_type == "buyer",
                SellerChat.is_read == False
            )
        ).group_by(SellerChat.seller_conversation_id)
    )
    unread = dict(unread_result.all())
    # Fallback: по order_id если conversation_id пустой (старые данные)
    order_unread = await session.execute(
        select(SellerChat.seller_order_id, func.count(SellerChat.id).label("c"))
        .join(SellerOrder, SellerChat.seller_order_id == SellerOrder.id)
        .where(and_(
            SellerOrder.seller_id == seller.id,
            SellerChat.sender_type == "buyer",
            SellerChat.is_read == False,
            SellerChat.seller_conversation_id.is_(None)
        )).group_by(SellerChat.seller_order_id)
    )
    for row in order_unread.all():
        if row[0]:
            unread[("order", row[0])] = row[1]
    from seller_bot.keyboards.inline import seller_main_menu
    if not unread:
        await callback.message.edit_text(
            "💬 <b>Messages</b>\n\nNo unread messages.",
            reply_markup=seller_main_menu(unread_count=0, actor_role=seller_actor.role),
        )
    else:
        buttons = []
        for k, count in unread.items():
            if isinstance(k, tuple) and k[0] == "order":
                buttons.append([InlineKeyboardButton(text=f"📦 Order #{k[1]} ({count} new)", callback_data=f"seller_chat:{k[1]}")])
            else:
                conv_id = k
                r = await session.execute(select(SellerConversation).where(
                    and_(SellerConversation.id == conv_id, SellerConversation.seller_id == seller.id)
                ))
                conv = r.scalar_one_or_none()
                if conv:
                    if seller_actor.is_helper and seller_actor.role == "support_helper" and conv.assigned_helper_id not in (None, seller_actor.helper.id):
                        continue
                    label = await _get_conv_button_label(session, conv)
                    buttons.append([InlineKeyboardButton(text=f"📦 {label} ({count} new)", callback_data=f"seller_chat_conv:{conv_id}")])
                    mini_app_url = _seller_mini_app_url(conv_id)
                    if mini_app_url:
                        buttons.append([InlineKeyboardButton(text=f"🖥 Mini App: {label}", web_app=WebAppInfo(url=mini_app_url))])
        buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="seller_menu")])
        await callback.message.edit_text(
            f"💬 <b>Chats</b>\n\nYou have messages from {len(unread)} buyer(s):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    await callback.answer()
