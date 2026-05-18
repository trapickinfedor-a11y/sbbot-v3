import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta, timezone

from shared.database.models import SellerOrder, SellerBank, Seller, SellerOrderDispute
from shared.services.seller_order_delivery_service import (
    mark_seller_order_completed,
    notify_buyer_order_completed,
)
from shared.utils.chat_filter import filter_message, is_message_blocked
from seller_bot.keyboards.inline import seller_orders_list, seller_order_keyboard, seller_main_menu
from seller_bot.utils import get_seller_unread_count

logger = logging.getLogger(__name__)
router = Router(name="seller_orders")

ALLOWED_RESULT_EXTENSIONS = {".txt", ".pdf", ".jpg", ".jpeg", ".png", ".zip"}
ALLOWED_RESULT_MIME_TYPES = {
    "text/plain",
    "application/pdf",
    "application/zip",
    "application/x-zip-compressed",
    "image/jpeg",
    "image/jpg",
    "image/png",
}
MAX_RESULT_FILE_SIZE = 20 * 1024 * 1024


class CompleteOrderStates(StatesGroup):
    waiting_result = State()


class SellerOrderStates(StatesGroup):
    waiting_result_text = State()
    waiting_result_file = State()


class DisputeStates(StatesGroup):
    waiting_evidence_text = State()
    waiting_evidence_file = State()
    waiting_appeal_reason = State()


@router.callback_query(F.data == "seller_orders")
async def orders_list_handler(callback: CallbackQuery, session: AsyncSession, seller, **kwargs):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    
    result = await session.execute(
        select(SellerOrder).where(
            SellerOrder.seller_id == seller.id
        ).order_by(SellerOrder.created_at.desc()).limit(30)
    )
    all_orders = list(result.scalars().all())
    # Сначала активные (approved, in_progress), потом остальные
    status_priority = {"approved": 0, "in_progress": 1, "disputed": 2, "pending_admin": 3, "completed": 4, "rejected": 5, "cancelled": 6}
    orders = sorted(all_orders, key=lambda o: (status_priority.get(o.status, 9), -o.id))
    
    if not orders:
        unread = await get_seller_unread_count(session, seller.id)
        await callback.message.edit_text(
            "📦 <b>My Orders</b>\n\n"
            "No orders yet. They will appear here when buyers purchase your banks.",
            reply_markup=seller_main_menu(unread_count=unread)
        )
    else:
        active = sum(1 for o in orders if o.status in ("approved", "in_progress"))
        await callback.message.edit_text(
            f"📦 <b>My Orders</b>\n\n"
            f"🟡 Active: {active}\n"
            f"📊 Total shown: {len(orders)}",
            reply_markup=seller_orders_list(orders)
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
    
    # Get bank info
    bank_result = await session.execute(
        select(SellerBank).where(SellerBank.id == order.seller_bank_id)
    )
    bank = bank_result.scalar_one_or_none()
    bank_name = bank.bank_name if bank else "Unknown"
    
    status_map = {
        "pending_admin": "⏳ Pending Admin Approval",
        "approved": "🟡 Approved - Waiting for you",
        "in_progress": "🔵 In Progress",
        "completed": "✅ Completed",
        "rejected": "❌ Rejected by Admin",
        "cancelled": "⚪ Cancelled",
        "disputed": "⚠️ Disputed",
    }
    
    text = (
        f"📦 <b>Order #{order.id}</b>\n\n"
        f"🏦 Bank: <b>{bank_name}</b>\n"
        f"📊 Status: {status_map.get(order.status, order.status)}\n"
        f"💰 Your earnings: <b>${order.price_for_seller:.2f}</b>\n"
        f"🔢 Quantity: {order.quantity}\n"
        f"📅 Created: {order.created_at.strftime('%Y-%m-%d %H:%M')}\n"
    )
    
    if order.admin_notes:
        text += f"\n📝 Admin notes: {order.admin_notes}\n"

    if order.status == "disputed" and getattr(order, "dispute_deadline_at", None):
        remaining = order.dispute_deadline_at - datetime.now(timezone.utc)
        if remaining.total_seconds() > 0:
            hours = int(remaining.total_seconds() // 3600)
            text += f"\n⚠️ Dispute decision window: {hours}h\n"
    elif getattr(order, "auto_complete_at", None):
        remaining = order.auto_complete_at - datetime.now(timezone.utc)
        if remaining.total_seconds() > 0:
            hours = int(remaining.total_seconds() // 3600)
            text += f"\n💸 Escrow release in: {hours}h\n"
    
    if bank:
        text += f"💬 Support chat: {'Enabled' if bank.has_chat else 'Disabled'}\n"
    if order.status in ("approved", "in_progress"):
        await callback.message.edit_text(
            text,
            reply_markup=seller_order_keyboard(order.id, has_chat=bool(bank.has_chat) if bank else True),
        )
    elif order.status == "disputed":
        # Check if there is an open dispute and whether seller can still respond/appeal
        dispute_res = await session.execute(
            select(SellerOrderDispute).where(SellerOrderDispute.order_id == order.id).order_by(SellerOrderDispute.id.desc())
        )
        dispute = dispute_res.scalars().first()
        dispute_kb_rows = []
        if dispute:
            if dispute.status in ("open", "seller_responded"):
                dispute_kb_rows.append([InlineKeyboardButton(
                    text="📎 Submit Evidence",
                    callback_data=f"seller_dispute_evidence:{order.id}:{dispute.id}",
                )])
            if dispute.status == "resolved" and dispute.appeal_status is None:
                dispute_kb_rows.append([InlineKeyboardButton(
                    text="⚖️ Request Appeal",
                    callback_data=f"seller_dispute_appeal:{order.id}:{dispute.id}",
                )])
        dispute_kb_rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="seller_orders")])
        await callback.message.edit_text(
            text, reply_markup=InlineKeyboardMarkup(inline_keyboard=dispute_kb_rows)
        )
    else:
        back_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back", callback_data="seller_orders")]
        ])
        await callback.message.edit_text(text, reply_markup=back_kb)

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
    
    order.status = "in_progress"
    order.taken_at = datetime.now(timezone.utc)
    await session.commit()
    
    await state.set_state(SellerOrderStates.waiting_result_text)
    await state.update_data(order_id=order_id)
    
    await callback.message.edit_text(
        f"✅ <b>Complete Order #{order_id}</b>\n\n"
        "Send the result for the buyer.\n"
        "You can send text or a file.\n\n"
        "⚠️ <b>Important:</b> Do not include usernames, links, phone numbers, or other contact information.\n\n"
        "Send /cancel to go back."
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_complete_file:"))
async def complete_order_file_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, **kwargs):
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

    order.status = "in_progress"
    order.taken_at = order.taken_at or datetime.now(timezone.utc)
    await session.commit()

    await state.set_state(SellerOrderStates.waiting_result_file)
    await state.update_data(order_id=order_id)

    await callback.message.edit_text(
        f"📎 <b>Complete Order #{order_id} with File</b>\n\n"
        "Send the file for the buyer.\n\n"
        "⚠️ Allowed formats: .txt, .pdf, .jpg, .png, .zip\n"
        "Max size: 20MB\n"
        "Do not include usernames, links, phone numbers, or other contact information in the file name.\n\n"
        "Send /cancel to go back."
    )
    await callback.answer()


@router.message(CompleteOrderStates.waiting_result, F.text)
@router.message(SellerOrderStates.waiting_result_text, F.text)
async def complete_order_result(message: Message, state: FSMContext, session: AsyncSession, seller, **kwargs):
    if message.text == "/cancel":
        await state.clear()
        unread = await get_seller_unread_count(session, seller.id)
        await message.answer("❌ Cancelled.", reply_markup=seller_main_menu(unread_count=unread))
        return
    
    data = await state.get_data()
    order_id = data["order_id"]
    await state.clear()
    
    result = await session.execute(
        select(SellerOrder).where(
            and_(SellerOrder.id == order_id, SellerOrder.seller_id == seller.id)
        )
    )
    order = result.scalar_one_or_none()
    
    if not order:
        await message.answer("❌ Order not found.")
        return

    raw_text = message.text or ""
    if is_message_blocked(raw_text):
        unread = await get_seller_unread_count(session, seller.id)
        await message.answer(
            "❌ Your message contains only contact information and was blocked.",
            reply_markup=seller_main_menu(unread_count=unread),
        )
        return

    filtered_text = filter_message(raw_text)
    was_filtered = filtered_text != raw_text

    bank = await mark_seller_order_completed(session, order, seller, result_text=filtered_text)
    
    unread = await get_seller_unread_count(session, seller.id)
    warning_text = "\n⚠️ Contact information was removed from your message." if was_filtered else ""
    await message.answer(
        f"✅ <b>Order #{order_id} completed!</b>\n\n"
        f"💰 You earned: ${order.price_for_seller:.2f}\n"
        f"The buyer will be notified.{warning_text}",
        reply_markup=seller_main_menu(unread_count=unread)
    )
    
    await notify_buyer_order_completed(session, order, result_text=filtered_text)


@router.message(CompleteOrderStates.waiting_result, F.document)
@router.message(CompleteOrderStates.waiting_result, F.photo)
@router.message(SellerOrderStates.waiting_result_file, F.document)
@router.message(SellerOrderStates.waiting_result_file, F.photo)
async def complete_order_file(message: Message, state: FSMContext, session: AsyncSession, seller, **kwargs):
    data = await state.get_data()
    order_id = data["order_id"]
    await state.clear()
    
    result = await session.execute(
        select(SellerOrder).where(
            and_(SellerOrder.id == order_id, SellerOrder.seller_id == seller.id)
        )
    )
    order = result.scalar_one_or_none()
    
    if not order:
        await message.answer("❌ Order not found.")
        return

    raw_document_name = (
        (message.document.file_name if message.document else None)
        or "result_photo.jpg"
    )
    if message.document:
        document_size = int(message.document.file_size or 0)
        if document_size > MAX_RESULT_FILE_SIZE:
            unread = await get_seller_unread_count(session, seller.id)
            await message.answer(
                "❌ File is too large. Maximum size is 20MB.",
                reply_markup=seller_main_menu(unread_count=unread),
            )
            return
        document_name_lower = raw_document_name.lower()
        if not any(document_name_lower.endswith(ext) for ext in ALLOWED_RESULT_EXTENSIONS):
            unread = await get_seller_unread_count(session, seller.id)
            await message.answer(
                "❌ Unsupported file format. Allowed: .txt, .pdf, .jpg, .png, .zip",
                reply_markup=seller_main_menu(unread_count=unread),
            )
            return
        mime_type = (message.document.mime_type or "").lower()
        if mime_type and mime_type not in ALLOWED_RESULT_MIME_TYPES:
            unread = await get_seller_unread_count(session, seller.id)
            await message.answer(
                "❌ Unsupported file type. Allowed: TXT, PDF, JPG, PNG, ZIP.",
                reply_markup=seller_main_menu(unread_count=unread),
            )
            return
    elif message.photo and int(message.photo[-1].file_size or 0) > MAX_RESULT_FILE_SIZE:
        unread = await get_seller_unread_count(session, seller.id)
        await message.answer(
            "❌ Photo is too large. Maximum size is 20MB.",
            reply_markup=seller_main_menu(unread_count=unread),
        )
        return
    if raw_document_name and is_message_blocked(raw_document_name):
        unread = await get_seller_unread_count(session, seller.id)
        await message.answer(
            "❌ File name contains only contact information and was blocked.",
            reply_markup=seller_main_menu(unread_count=unread),
        )
        return
    if raw_document_name and filter_message(raw_document_name) != raw_document_name:
        unread = await get_seller_unread_count(session, seller.id)
        await message.answer(
            "❌ File name contains contact information and was blocked.",
            reply_markup=seller_main_menu(unread_count=unread),
        )
        return
    safe_document_name = filter_message(raw_document_name) or "result"

    await mark_seller_order_completed(
        session,
        order,
        seller,
        document_file_id=message.document.file_id if message.document else message.photo[-1].file_id,
        document_name=safe_document_name,
        media_type="document" if message.document else "photo",
    )
    
    unread = await get_seller_unread_count(session, seller.id)
    await message.answer(
        f"✅ <b>Order #{order_id} completed with file!</b>\n\n"
        f"💰 You earned: ${order.price_for_seller:.2f}\n"
        f"The buyer will be notified.",
        reply_markup=seller_main_menu(unread_count=unread)
    )
    
    await notify_buyer_order_completed(
        session,
        order,
        document_file_id=message.document.file_id if message.document else message.photo[-1].file_id,
        document_name=safe_document_name,
        media_type="document" if message.document else "photo",
    )


# ─── Dispute: Evidence Submission ────────────────────────────────────────────

@router.callback_query(F.data.startswith("seller_dispute_evidence:"))
async def dispute_evidence_start(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, **kwargs
):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    _, order_id_str, dispute_id_str = callback.data.split(":")
    order_id = int(order_id_str)
    dispute_id = int(dispute_id_str)

    order = await session.get(SellerOrder, order_id)
    if not order or order.seller_id != seller.id:
        await callback.answer("❌ Order not found", show_alert=True)
        return

    await state.set_state(DisputeStates.waiting_evidence_text)
    await state.update_data(dispute_order_id=order_id, dispute_id=dispute_id)
    await callback.message.edit_text(
        f"📎 <b>Submit Evidence — Order #{order_id}</b>\n\n"
        "Describe what happened and attach any proof (screenshots, files, photos).\n\n"
        "You can send:\n"
        "• A text message with your explanation\n"
        "• A photo or document as evidence\n\n"
        "Send /cancel to go back.",
    )
    await callback.answer()


@router.message(DisputeStates.waiting_evidence_text, F.text)
async def dispute_evidence_text(
    message: Message, state: FSMContext, session: AsyncSession, seller, **kwargs
):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back to Orders", callback_data="seller_orders")]
        ]))
        return

    data = await state.get_data()
    dispute_id = data["dispute_id"]
    order_id = data["dispute_order_id"]
    await state.clear()

    dispute = await session.get(SellerOrderDispute, dispute_id)
    if not dispute:
        await message.answer("❌ Dispute not found.")
        return

    evidence = dict(dispute.seller_evidence or {})
    evidence["text"] = (message.text or "")[:4000]
    evidence["submitted_at"] = datetime.now(timezone.utc).isoformat()
    dispute.seller_evidence = evidence
    if dispute.status == "open":
        dispute.status = "seller_responded"
        dispute.seller_responded_at = datetime.now(timezone.utc)
    await session.commit()

    await message.answer(
        f"✅ <b>Evidence submitted for Order #{order_id}.</b>\n\n"
        "The admin will review your evidence and make a decision.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back to Orders", callback_data="seller_orders")]
        ]),
    )


@router.message(DisputeStates.waiting_evidence_text, F.document | F.photo)
async def dispute_evidence_file(
    message: Message, state: FSMContext, session: AsyncSession, seller, **kwargs
):
    data = await state.get_data()
    dispute_id = data["dispute_id"]
    order_id = data["dispute_order_id"]
    await state.clear()

    dispute = await session.get(SellerOrderDispute, dispute_id)
    if not dispute:
        await message.answer("❌ Dispute not found.")
        return

    file_id = (
        message.document.file_id if message.document
        else message.photo[-1].file_id if message.photo
        else None
    )
    evidence = dict(dispute.seller_evidence or {})
    if file_id:
        evidence["file_id"] = file_id
        evidence["media_type"] = "document" if message.document else "photo"
    evidence["submitted_at"] = datetime.now(timezone.utc).isoformat()
    if message.caption:
        evidence["text"] = message.caption[:4000]
    dispute.seller_evidence = evidence
    if dispute.status == "open":
        dispute.status = "seller_responded"
        dispute.seller_responded_at = datetime.now(timezone.utc)
    await session.commit()

    await message.answer(
        f"✅ <b>Evidence file submitted for Order #{order_id}.</b>\n\n"
        "The admin will review your evidence and make a decision.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back to Orders", callback_data="seller_orders")]
        ]),
    )


# ─── Dispute: Appeal Request ──────────────────────────────────────────────────

@router.callback_query(F.data.startswith("seller_dispute_appeal:"))
async def dispute_appeal_start(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, **kwargs
):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    _, order_id_str, dispute_id_str = callback.data.split(":")
    order_id = int(order_id_str)
    dispute_id = int(dispute_id_str)

    dispute = await session.get(SellerOrderDispute, dispute_id)
    if not dispute or dispute.appeal_status is not None:
        await callback.answer("❌ Appeal not available for this dispute.", show_alert=True)
        return

    await state.set_state(DisputeStates.waiting_appeal_reason)
    await state.update_data(dispute_order_id=order_id, dispute_id=dispute_id)
    await callback.message.edit_text(
        f"⚖️ <b>Request Appeal — Order #{order_id}</b>\n\n"
        "Explain why you believe the dispute decision was incorrect.\n"
        "Provide specific reasons and any additional evidence you have.\n\n"
        "Send /cancel to go back.",
    )
    await callback.answer()


@router.message(DisputeStates.waiting_appeal_reason, F.text)
async def dispute_appeal_submit(
    message: Message, state: FSMContext, session: AsyncSession, seller, **kwargs
):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back to Orders", callback_data="seller_orders")]
        ]))
        return

    data = await state.get_data()
    dispute_id = data["dispute_id"]
    order_id = data["dispute_order_id"]
    await state.clear()

    dispute = await session.get(SellerOrderDispute, dispute_id)
    if not dispute:
        await message.answer("❌ Dispute not found.")
        return
    if dispute.appeal_status is not None:
        await message.answer("❌ An appeal was already submitted for this dispute.")
        return

    dispute.appeal_status = "pending"
    dispute.appeal_reason = (message.text or "")[:2000]
    dispute.appeal_requested_at = datetime.now(timezone.utc)
    await session.commit()

    await message.answer(
        f"⚖️ <b>Appeal submitted for Order #{order_id}.</b>\n\n"
        "An admin will review your appeal and contact you.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back to Orders", callback_data="seller_orders")]
        ]),
    )
