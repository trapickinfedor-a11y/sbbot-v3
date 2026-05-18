from __future__ import annotations

"""
Buyer's list of bank orders (SellerOrder) with access to chat.
Один чат на селлера — при клике на заказ открывается общий чат с этим селлером.
"""
import logging
from datetime import datetime, timedelta, timezone
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from shared.database.models import SellerOrder, SellerBank
from shared.services.seller_dispute_service import SellerDisputeService
from shared.services.seller_conversation_service import get_conversation_from_order
from shared.services.seller_order_delivery_service import (
    build_buyer_order_actions_keyboard,
    build_buyer_order_reveal_keyboard,
    build_buyer_order_rating_keyboard,
    build_buyer_return_reason_keyboard,
    confirm_seller_order,
    format_buyer_order_ready_text,
    get_seller_order_effective_window_minutes,
    format_seller_order_window_label,
    get_seller_order_policy,
    get_seller_order_v24_windows,
    get_seller_order_result_document,
    get_seller_order_result_text,
    is_seller_order_data_revealed,
    mark_seller_order_data_revealed,
    request_seller_order_return,
    save_seller_order_rating,
)
from shared.services.guarantee_policy_service import is_guarantee_active
from mirror_bot.utils.message_utils import safe_edit_message

logger = logging.getLogger(__name__)
router = Router(name="buyer_orders")

STATUS_LABELS = {
    "pending_admin": "⏳ Pending",
    "approved": "🟡 Approved",
    "in_progress": "🔵 In Progress",
    "completed": "✅ Completed",
    "rejected": "❌ Rejected",
    "cancelled": "⚪ Cancelled",
    "disputed": "⚠️ Disputed",
    "moderation_review": "🛡 Moderation Review",
}


async def _render_order_card(session: AsyncSession, order: SellerOrder, buttons) -> tuple[str, InlineKeyboardMarkup]:
    bank = await session.scalar(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
    bank_name = bank.bank_name if bank else "Bank"
    status_label = STATUS_LABELS.get(order.status, order.status)
    policy = get_seller_order_policy(order, bank)
    data_revealed = is_seller_order_data_revealed(order)
    text = (
        f"📦 **Order #{order.id}**\n\n"
        f"🏦 {bank_name}\n"
        f"📊 Status: {status_label}\n"
        f"💰 Paid: ${order.price_for_buyer:.2f}\n"
        f"🔢 Qty: {order.quantity}\n"
    )
    if order.check_confirmed_at:
        text += "\n✅ Product confirmed."
        if order.buyer_rating:
            text += f"\n⭐ Your rating: {order.buyer_rating}."
    elif order.status == "cancelled":
        text += "\n↩️ Product returned/cancelled."
    elif order.status == "moderation_review":
        text += "\n🛡 Return/dispute is under moderation review."
    elif order.status == "completed":
        if bank and bank.has_chat:
            if data_revealed:
                if is_guarantee_active(order.check_expires_at):
                    text += "\n👍👎 Rate the product or report an issue while the guarantee window is active."
                else:
                    text += "\n👍👎 Guarantee window expired. Only rating is still available."
            else:
                effective_window = get_seller_order_effective_window_minutes(order, policy)
                text += f"\n✅ Press Confirm to reveal the material. Guarantee window: {format_seller_order_window_label(effective_window)}."
        else:
            text += "\n⏳ Check the material, then rate it or report an issue during the check window."

    keyboard_rows: list[list[InlineKeyboardButton]] = []
    if bank and bank.has_chat and order.status in ("approved", "in_progress"):
        conv = await get_conversation_from_order(session, order)
        keyboard_rows.append([InlineKeyboardButton(text="💬 Open Seller Chat", callback_data=f"buyer_chat_conv:{conv.id}:{order.id}")])
    if order.status == "completed" and not order.check_confirmed_at and order.status != "cancelled":
        if bank and bank.has_chat and not data_revealed:
            reveal_kb = await build_buyer_order_reveal_keyboard(session, order, bank)
            keyboard_rows.extend(reveal_kb.inline_keyboard[:-1])
        else:
            action_kb = await build_buyer_order_actions_keyboard(session, order, bank)
            keyboard_rows.extend(action_kb.inline_keyboard[:-1])
    if order.check_confirmed_at and not order.buyer_rating:
        rating_kb = build_buyer_order_rating_keyboard(order.id)
        keyboard_rows.extend(rating_kb.inline_keyboard[:-1])
    keyboard_rows.append([InlineKeyboardButton(text=buttons.BACK, callback_data="buyer_my_orders")])
    return text, InlineKeyboardMarkup(inline_keyboard=keyboard_rows)


@router.callback_query(F.data == "buyer_my_orders")
async def buyer_my_orders_list(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, texts, buttons, **kwargs):
    """Список заказов. Клик → чат с селлером (один на покупателя)"""
    result = await session.execute(
        select(SellerOrder)
        .where(
            and_(
                SellerOrder.buyer_user_id == callback.from_user.id,
                SellerOrder.mirror_bot_id == mirror_bot_id
            )
        )
        .order_by(SellerOrder.created_at.desc())
        .limit(50)
    )
    orders = list(result.scalars().all())

    if not orders:
        text = "📦 **My Bank Orders**\n\n_You have no bank orders yet._"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=buttons.BACK, callback_data="back_main")]
        ])
        await safe_edit_message(callback, text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer()
        return

    kb_buttons = []
    for order in orders:
        bank_result = await session.execute(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
        bank = bank_result.scalar_one_or_none()
        bank_name = bank.bank_name if bank else "Bank"
        status_label = STATUS_LABELS.get(order.status, order.status)
        if bank and bank.has_chat and order.status in ("approved", "in_progress"):
            conv = await get_conversation_from_order(session, order)
            callback_data = f"buyer_chat_conv:{conv.id}:{order.id}"
        else:
            callback_data = f"buyer_order_detail:{order.id}"
        kb_buttons.append([
            InlineKeyboardButton(
                text=f"{status_label} #{order.id} | {bank_name} | ${order.price_for_buyer:.2f}",
                callback_data=callback_data
            )
        ])
    kb_buttons.append([InlineKeyboardButton(text=buttons.BACK, callback_data="back_main")])

    text = "📦 **My Bank Orders**\n\n_Select an order to open chat or actions:_"
    keyboard = InlineKeyboardMarkup(inline_keyboard=kb_buttons)
    await safe_edit_message(callback, text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("buyer_order_detail:"))
async def buyer_order_detail(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, buttons, **kwargs):
    order_id = int(callback.data.split(":")[1])
    order = await session.scalar(
        select(SellerOrder).where(
            and_(
                SellerOrder.id == order_id,
                SellerOrder.buyer_user_id == callback.from_user.id,
                SellerOrder.mirror_bot_id == mirror_bot_id,
            )
        )
    )
    if not order:
        await callback.answer("Order not found", show_alert=True)
        return
    text, keyboard = await _render_order_card(session, order, buttons)
    await safe_edit_message(callback, text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("buyer_order_confirm:"))
async def buyer_order_confirm(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, buttons, **kwargs):
    order_id = int(callback.data.split(":")[1])
    order = await session.scalar(
        select(SellerOrder).where(
            and_(
                SellerOrder.id == order_id,
                SellerOrder.buyer_user_id == callback.from_user.id,
                SellerOrder.mirror_bot_id == mirror_bot_id,
            )
        )
    )
    if not order:
        await callback.answer("Order not found", show_alert=True)
        return
    if not await confirm_seller_order(session, order, auto=False):
        await callback.answer("This order is already confirmed or unavailable.", show_alert=True)
        return
    text, keyboard = await _render_order_card(session, order, buttons)
    await safe_edit_message(callback, text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer("✅ Product confirmed")


@router.callback_query(F.data.startswith("buyer_order_reveal:"))
async def buyer_order_reveal(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, buttons, **kwargs):
    order_id = int(callback.data.split(":")[1])
    order = await session.scalar(
        select(SellerOrder).where(
            and_(
                SellerOrder.id == order_id,
                SellerOrder.buyer_user_id == callback.from_user.id,
                SellerOrder.mirror_bot_id == mirror_bot_id,
            )
        )
    )
    if not order:
        await callback.answer("Order not found", show_alert=True)
        return

    bank = await session.scalar(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
    policy = get_seller_order_policy(order, bank)
    if order.status != "completed" or order.check_confirmed_at or not policy.requires_reveal_confirmation:
        await callback.answer("This order cannot be revealed.", show_alert=True)
        return

    await mark_seller_order_data_revealed(session, order)
    bank_name = bank.bank_name if bank else "Bank"
    text = format_buyer_order_ready_text(order, bank_name, bool(getattr(bank, "has_chat", True)), policy, data_revealed=True)
    action_kb = await build_buyer_order_actions_keyboard(session, order, bank)
    result_text = get_seller_order_result_text(order)
    document_file_id, document_name, media_type = get_seller_order_result_document(order)

    if document_file_id:
        if media_type == "photo":
            await callback.bot.send_photo(
                order.buyer_user_id,
                photo=document_file_id,
                caption=f"{text}\n\n📎 Attached file: {document_name or 'result'}",
                parse_mode="HTML",
                reply_markup=action_kb,
            )
        else:
            await callback.bot.send_document(
                order.buyer_user_id,
                document=document_file_id,
                caption=f"{text}\n\n📎 Attached file: {document_name or 'result'}",
                parse_mode="HTML",
                reply_markup=action_kb,
            )
        await safe_edit_message(
            callback,
            "✅ **Material revealed.**\n\nA new message with the data has been sent.",
            reply_markup=action_kb,
            parse_mode="Markdown",
        )
    else:
        if result_text:
            text += f"\n\n<b>Result:</b>\n<code>{result_text}</code>"
        await safe_edit_message(callback, text, reply_markup=action_kb, parse_mode="HTML")

    await callback.answer("✅ Material revealed")


@router.callback_query(F.data.startswith("buyer_order_return:"))
async def buyer_order_return(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, buttons, **kwargs):
    order_id = int(callback.data.split(":")[1])
    order = await session.scalar(
        select(SellerOrder).where(
            and_(
                SellerOrder.id == order_id,
                SellerOrder.buyer_user_id == callback.from_user.id,
                SellerOrder.mirror_bot_id == mirror_bot_id,
            )
        )
    )
    if not order:
        await callback.answer("Order not found", show_alert=True)
        return
    await safe_edit_message(
        callback,
        "↩️ **Choose return reason**",
        reply_markup=build_buyer_return_reason_keyboard(order.id),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buyer_order_return_reason:"))
async def buyer_order_return_reason(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, buttons, **kwargs):
    _, _, order_id_raw, reason = callback.data.split(":", 3)
    order_id = int(order_id_raw)
    order = await session.scalar(
        select(SellerOrder).where(
            and_(
                SellerOrder.id == order_id,
                SellerOrder.buyer_user_id == callback.from_user.id,
                SellerOrder.mirror_bot_id == mirror_bot_id,
            )
        )
    )
    if not order:
        await callback.answer("Order not found", show_alert=True)
        return
    if not await request_seller_order_return(session, order, reason=reason):
        await callback.answer("Return window expired or order already confirmed.", show_alert=True)
        return
    text, keyboard = await _render_order_card(session, order, buttons)
    await safe_edit_message(callback, text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer("⏳ Sent to moderation")


@router.callback_query(F.data.startswith("buyer_order_report:"))
async def buyer_order_report(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, buttons, **kwargs):
    order_id = int(callback.data.split(":")[1])
    order = await session.scalar(
        select(SellerOrder).where(
            and_(
                SellerOrder.id == order_id,
                SellerOrder.buyer_user_id == callback.from_user.id,
                SellerOrder.mirror_bot_id == mirror_bot_id,
            )
        )
    )
    if not order:
        await callback.answer("Order not found", show_alert=True)
        return
    if order.status not in ("completed", "approved", "in_progress"):
        await callback.answer("Cannot send report for this order.", show_alert=True)
        return
    if not is_guarantee_active(order.check_expires_at):
        await callback.answer("Guarantee window expired", show_alert=True)
        return
    bank = await session.scalar(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
    policy = get_seller_order_policy(order, bank)
    now = datetime.now(timezone.utc)
    await SellerDisputeService.open_dispute(
        session,
        order=order,
        opened_by=callback.from_user.id,
        reason="buyer_report",
        description="Buyer opened report from order card",
        buyer_evidence={
            "source": "buyer_order_card",
            "opened_at": now.isoformat(),
            "order_id": order.id,
            "buyer_user_id": callback.from_user.id,
            "seller_id": order.seller_id,
            "trigger": "order_card",
        },
    )
    order.report_status = "reported"
    order.reported_at = now
    await session.commit()
    try:
        from shared.services.admin_notification_service import AdminNotificationService
        from shared.services.bot_pool import get_seller_bot

        bank_name = bank.bank_name if bank else "Bank"
        await AdminNotificationService.notify_dispute(order.id, bank_name, callback.from_user.id)
        seller = await session.scalar(select(Seller).where(Seller.id == order.seller_id))
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
        logger.error(f"Failed to notify about order-card dispute: {e}")
    conv = await get_conversation_from_order(session, order)
    report_text = "⚠️ Report created. Open the private seller chat for this order."
    if policy.report_requires_video:
        report_text = "⚠️ Report created. Open the private seller chat and send video proof for this order."
    await safe_edit_message(
        callback,
        report_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Open Seller Chat", callback_data=f"buyer_chat_conv:{conv.id}:{order.id}")],
            [InlineKeyboardButton(text=buttons.BACK, callback_data=f"buyer_order_detail:{order.id}")],
        ]),
        parse_mode=None,
    )
    await callback.answer("⚠️ Report sent")


@router.callback_query(F.data.startswith("buyer_order_rate:"))
async def buyer_order_rate(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, buttons, **kwargs):
    _, _, order_id_raw, rating = callback.data.split(":", 3)
    order_id = int(order_id_raw)
    order = await session.scalar(
        select(SellerOrder).where(
            and_(
                SellerOrder.id == order_id,
                SellerOrder.buyer_user_id == callback.from_user.id,
                SellerOrder.mirror_bot_id == mirror_bot_id,
            )
        )
    )
    if not order:
        await callback.answer("Order not found", show_alert=True)
        return
    if not await save_seller_order_rating(session, order, rating=rating):
        await callback.answer("Rating unavailable for this order.", show_alert=True)
        return
    await safe_edit_message(
        callback,
        "⭐ Feedback saved.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=getattr(buttons, "BACK_TO_MENU", getattr(buttons, "BACK", "Back")), callback_data="back_main")]
        ]),
        parse_mode=None,
    )
    await callback.answer("⭐ Rating saved")


# ──────────────────────────────────────────────────────────────────────────
# Worker Info Request — buyer replies to a worker's information request
# ──────────────────────────────────────────────────────────────────────────
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import and_

from shared.database.models import Order, WorkerOrder, User, Worker


class InfoReplyFSM(StatesGroup):
    awaiting_reply = State()


@router.callback_query(F.data.startswith("reply_info_request:"))
async def cb_reply_info_request(callback: CallbackQuery, session: AsyncSession, state: FSMContext, **kwargs):
    """Buyer taps 'Reply to Worker' button on an order where info was requested."""
    order_id = int(callback.data.split(":")[1])
    await state.update_data(info_reply_order_id=order_id)
    await state.set_state(InfoReplyFSM.awaiting_reply)
    await callback.message.answer(
        "✍️ <b>Reply to Worker</b>\n\n"
        "Please type your answer to the worker's question:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(InfoReplyFSM.awaiting_reply)
async def fsm_send_info_reply(message: Message, session: AsyncSession, state: FSMContext, **kwargs):
    """Buyer typed their reply — forward to worker via Support Bot."""
    data = await state.get_data()
    order_id = data.get("info_reply_order_id")
    if not order_id:
        await state.clear()
        return

    reply_text = (message.text or "").strip()
    if not reply_text:
        await message.answer("❌ Please provide a non-empty reply.")
        return

    # Update WorkerOrder — resume timer, save reply
    wo = await session.scalar(
        select(WorkerOrder).where(WorkerOrder.order_id == order_id)
    )
    if wo:
        wo.info_replied_at = datetime.now(timezone.utc)
        wo.timer_paused_at = None  # resume timer
        await session.commit()

    # Notify the worker via Support Bot
    if wo and wo.worker_id:
        worker = await session.get(Worker, wo.worker_id)
        if worker:
            try:
                from support_bot.config import support_bot_config
                from aiogram import Bot as AiogramBot
                support_token = getattr(support_bot_config, "bot_token", None)
                if support_token:
                    support_bot = AiogramBot(token=support_token)
                    await support_bot.send_message(
                        worker.telegram_id,
                        f"💬 <b>Buyer replied to your info request (Order #{order_id})</b>\n\n"
                        f"<blockquote>{reply_text}</blockquote>\n\n"
                        f"The order timer has been resumed.",
                        parse_mode="HTML",
                    )
                    await support_bot.session.close()
            except Exception as exc:
                import logging
                logging.getLogger(__name__).warning(
                    "Could not notify worker about buyer reply: %s", exc
                )

    await state.clear()
    await message.answer(
        "✅ <b>Your reply has been sent to the worker.</b>\n\n"
        "The worker will continue processing your order.",
        parse_mode="HTML",
    )
