from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import MirrorBot, Seller, SellerBank, SellerChat, SellerOrder, SellerOrderDispute, SystemSetting, User
from shared.services.bot_pool import get_mirror_bot_instance
from shared.services.guarantee_policy_service import (
    format_guarantee_window,
    get_seller_guarantee_policy,
    is_guarantee_active,
)
from shared.services.ledger_service import LedgerService
from shared.services.nocodb_service import NocoDBService
from shared.services.seller_conversation_service import get_conversation_from_order

logger = logging.getLogger(__name__)

RETURN_REASON_OPTIONS = (
    ("not_as_described", "Not as described"),
    ("invalid_data", "Invalid data"),
    ("no_access", "No access"),
    ("seller_unresponsive", "Seller unresponsive"),
    ("other", "Other"),
)

RATING_REASON_OPTIONS = (
    ("wrong_description", "Wrong description"),
    ("bad_material", "Bad material"),
    ("seller_slow", "Seller slow"),
    ("no_help", "No help"),
    ("other", "Other"),
)


@dataclass(frozen=True)
class SellerOrderPolicy:
    check_window_minutes: int
    requires_reveal_confirmation: bool
    report_requires_video: bool = False
    allows_return: bool = True


def _sync_bank_stock_flags(bank: SellerBank | None) -> None:
    if not bank:
        return
    free_stock = max(0, int(bank.stock_count or 0) - int(getattr(bank, "reserved_count", 0) or 0))
    bank.is_in_stock = free_stock > 0


def _format_window_label(minutes: int) -> str:
    return format_guarantee_window(minutes)


def format_seller_order_window_label(minutes: int) -> str:
    return _format_window_label(minutes)


async def _get_system_setting_int(session: AsyncSession, key: str, default: int) -> int:
    row = await session.scalar(select(SystemSetting).where(SystemSetting.key == key))
    if not row or row.value in (None, ""):
        return default
    try:
        return int(str(row.value).strip())
    except (TypeError, ValueError):
        return default


async def get_seller_order_v24_windows(session: AsyncSession) -> tuple[int, int]:
    dispute_hours = await _get_system_setting_int(session, "DISPUTE_WINDOW_HOURS", 24)
    auto_complete_hours = await _get_system_setting_int(session, "AUTO_COMPLETE_HOURS", dispute_hours)
    return dispute_hours, auto_complete_hours


async def get_seller_dynamic_hold_hours(session: AsyncSession, seller: Seller | None, buyer: User | None = None) -> int:
    top_seller_hours = await _get_system_setting_int(session, "ESCROW_HOLD_TOP_SELLER_HOURS", 12)
    standard_hours = await _get_system_setting_int(session, "ESCROW_HOLD_STANDARD_HOURS", 48)
    new_seller_hours = await _get_system_setting_int(session, "ESCROW_HOLD_NEW_SELLER_HOURS", 72)
    risky_buyer_hours = await _get_system_setting_int(session, "ESCROW_HOLD_RISKY_BUYER_HOURS", new_seller_hours)
    new_seller_sales_threshold = await _get_system_setting_int(session, "ESCROW_NEW_SELLER_SALES_THRESHOLD", 10)
    top_seller_score_threshold_raw = await _get_system_setting_int(session, "ESCROW_TOP_SELLER_SCORE_X10", 48)
    buyer_risk_threshold = await _get_system_setting_int(session, "BUYER_TRUST_SCORE_RISK_THRESHOLD", 30)

    if not seller:
        return standard_hours
    total_orders = int(getattr(seller, "total_orders", 0) or 0)
    if total_orders < new_seller_sales_threshold:
        return new_seller_hours
    if buyer and int(getattr(buyer, "trust_score", 100) or 100) < buyer_risk_threshold:
        return risky_buyer_hours

    likes = int(getattr(seller, "likes_count", 0) or 0)
    dislikes = int(getattr(seller, "dislikes_count", 0) or 0)
    total_feedback = likes + dislikes
    reputation_score_x10 = 0
    if total_feedback > 0:
        reputation_score_x10 = round((likes / total_feedback) * 50)
    if reputation_score_x10 >= top_seller_score_threshold_raw:
        return top_seller_hours
    return standard_hours


def get_seller_order_policy(order: SellerOrder, bank: SellerBank | None) -> SellerOrderPolicy:
    product_type = (getattr(order, "product_type", None) or getattr(bank, "product_type", None) or "").strip().lower()
    product_subtype = (getattr(order, "product_subtype", None) or getattr(bank, "product_subtype", None) or "").strip().lower()
    bank_name = (getattr(bank, "bank_name", None) or "").strip().lower()
    has_chat = bool(getattr(bank, "has_chat", True))
    guarantee = get_seller_guarantee_policy(
        product_type=product_type,
        product_subtype=product_subtype,
        bank_name=bank_name,
    )
    return SellerOrderPolicy(
        check_window_minutes=guarantee.minutes,
        requires_reveal_confirmation=has_chat and guarantee.requires_reveal_confirmation,
        report_requires_video=guarantee.report_requires_video,
        allows_return=guarantee.allows_return,
    )


def get_seller_order_effective_window_minutes(order: SellerOrder, policy: SellerOrderPolicy) -> int:
    return int(getattr(order, "check_window_minutes", 0) or policy.check_window_minutes)


def is_seller_order_data_revealed(order: SellerOrder) -> bool:
    return bool(order.check_started_at)


def get_seller_order_result_text(order: SellerOrder) -> str | None:
    if isinstance(order.result_data, dict):
        return order.result_data.get("text")
    return None


def get_seller_order_result_document(order: SellerOrder) -> tuple[str | None, str | None, str]:
    document_file_id = None
    if isinstance(order.files, list) and order.files:
        document_file_id = order.files[0]
    document_name = order.result_data.get("file_name") if isinstance(order.result_data, dict) else None
    media_type = order.result_data.get("media_type") if isinstance(order.result_data, dict) else None
    return document_file_id, document_name, (media_type or "document")


async def mark_seller_order_data_revealed(session: AsyncSession, order: SellerOrder) -> None:
    if order.check_started_at:
        return
    order.check_started_at = datetime.now(timezone.utc)
    await session.commit()


async def release_seller_order_reservation(session: AsyncSession, order: SellerOrder) -> SellerBank | None:
    bank = await session.scalar(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
    if not bank or order.reservation_released_at:
        return bank

    reserved_qty = int(order.reserved_quantity or order.quantity or 0)
    if reserved_qty > 0:
        bank.reserved_count = max(0, int(getattr(bank, "reserved_count", 0) or 0) - reserved_qty)
    order.reservation_released_at = datetime.now(timezone.utc)
    _sync_bank_stock_flags(bank)
    return bank


def format_buyer_order_ready_text(
    order: SellerOrder,
    bank_name: str,
    has_chat: bool,
    policy: SellerOrderPolicy,
    *,
    data_revealed: bool,
) -> str:
    window_label = _format_window_label(get_seller_order_effective_window_minutes(order, policy))
    if has_chat and not data_revealed:
        video_note = "\n📹 Video proof is required for disputes in this category." if policy.report_requires_video else ""
        return (
            "✅ <b>Your order is ready!</b>\n\n"
            f"🏦 {bank_name}\n"
            f"📦 Order #{order.id}\n\n"
            f"🛡 Guarantee window: {window_label}.\n"
            "Press <b>✅ Confirm</b> to reveal the material.\n"
            f"After that you can open chat with the seller or send the order to moderation.{video_note}"
        )
    if has_chat:
        video_note = "\n📹 Video proof is required for disputes in this category." if policy.report_requires_video else ""
        action_note = "You can write to the seller, send the order to moderation, or confirm that the product works."
        if not policy.requires_reveal_confirmation:
            action_note = "You can write to the seller or send the order to moderation right away."
        return (
            "✅ <b>Your order is ready!</b>\n\n"
            f"🏦 {bank_name}\n"
            f"📦 Order #{order.id}\n\n"
            f"🛡 Guarantee window: {window_label}.\n"
            f"{action_note}{video_note}"
        )
    return (
        "✅ <b>Your order is ready!</b>\n\n"
        f"🏦 {bank_name}\n"
        f"📦 Order #{order.id}\n\n"
        f"⏳ You have {window_label} to check the material.\n"
        "If you do nothing, the order will be confirmed automatically."
    )


async def build_buyer_order_actions_keyboard(
    session: AsyncSession,
    order: SellerOrder,
    bank: SellerBank | None = None,
) -> InlineKeyboardMarkup:
    bank = bank or await session.scalar(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
    buttons: list[list[InlineKeyboardButton]] = []
    buttons.append([InlineKeyboardButton(text="👍 Like", callback_data=f"buyer_order_rate:{order.id}:like")])
    buttons.append([InlineKeyboardButton(text="👎 Dislike", callback_data=f"buyer_order_rate:{order.id}:dislike")])
    if is_guarantee_active(order.check_expires_at):
        buttons.append([InlineKeyboardButton(text="⚠️ Report Issue", callback_data=f"buyer_order_report:{order.id}")])
    buttons.append([InlineKeyboardButton(text="📦 My Orders", callback_data="buyer_my_orders")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def build_buyer_order_reveal_keyboard(
    session: AsyncSession,
    order: SellerOrder,
    bank: SellerBank | None = None,
) -> InlineKeyboardMarkup:
    bank = bank or await session.scalar(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
    has_chat = bool(getattr(bank, "has_chat", True))
    buttons: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="✅ Confirm", callback_data=f"buyer_order_reveal:{order.id}")]
    ]
    if has_chat:
        conv = await get_conversation_from_order(session, order)
        buttons.append([InlineKeyboardButton(text="💬 Write to Seller", callback_data=f"buyer_chat_conv:{conv.id}:{order.id}")])
        buttons.append([InlineKeyboardButton(text="🛡 Send to Moderation", callback_data=f"buyer_order_report:{order.id}")])
    buttons.append([InlineKeyboardButton(text="📦 My Orders", callback_data="buyer_my_orders")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_buyer_return_reason_keyboard(order_id: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"buyer_order_return_reason:{order_id}:{code}")]
        for code, label in RETURN_REASON_OPTIONS
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data=f"buyer_order_detail:{order_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_buyer_rating_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍 Like", callback_data=f"buyer_order_rate:{order_id}:like")],
        [InlineKeyboardButton(text="👎 Dislike", callback_data=f"buyer_order_rate:{order_id}:dislike")],
        [InlineKeyboardButton(text="⚠️ Report Issue", callback_data=f"buyer_order_report:{order_id}")],
        [InlineKeyboardButton(text="📦 My Orders", callback_data="buyer_my_orders")],
    ])


def build_buyer_order_rating_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return build_buyer_rating_keyboard(order_id)


async def mark_seller_order_completed(
    session: AsyncSession,
    order: SellerOrder,
    seller: Seller,
    *,
    result_text: str | None = None,
    document_file_id: str | None = None,
    document_name: str | None = None,
    media_type: str = "document",
) -> SellerBank | None:
    bank = await session.scalar(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
    buyer = await session.scalar(select(User).where(User.user_id == order.buyer_user_id))
    policy = get_seller_order_policy(order, bank)
    was_completed = bool(order.completed_at)
    dispute_window_hours, _ = await get_seller_order_v24_windows(session)
    escrow_hold_hours = await get_seller_dynamic_hold_hours(session, seller, buyer)
    dispute_window_minutes = dispute_window_hours * 60

    order.status = "completed"
    order.completed_at = datetime.now(timezone.utc)
    order.check_window_minutes = dispute_window_minutes
    order.check_started_at = None
    order.check_confirmed_at = None
    order.check_expires_at = datetime.now(timezone.utc) + timedelta(minutes=dispute_window_minutes)
    if hasattr(order, "auto_complete_at"):
        order.auto_complete_at = datetime.now(timezone.utc) + timedelta(hours=escrow_hold_hours)
    if hasattr(order, "dispute_deadline_at"):
        order.dispute_deadline_at = datetime.now(timezone.utc) + timedelta(hours=dispute_window_hours)
    order.buyer_rating = None
    order.buyer_rating_at = None
    order.buyer_rating_reason = None
    order.return_reason = None
    order.return_reason_comment = None
    order.return_requested_at = None

    if result_text is not None:
        order.result_data = {"text": result_text}
        order.files = None
        conversation = await get_conversation_from_order(session, order)
        session.add(
            SellerChat(
                seller_conversation_id=getattr(conversation, "id", None),
                seller_order_id=order.id,
                sender_type="seller",
                sender_id=seller.telegram_id,
                message_text=result_text,
                files=None,
            )
        )
    elif document_file_id is not None:
        order.files = [document_file_id]
        order.result_data = {
            "file_name": document_name or "result",
            "media_type": media_type or "document",
        }
        conversation = await get_conversation_from_order(session, order)
        session.add(
            SellerChat(
                seller_conversation_id=getattr(conversation, "id", None),
                seller_order_id=order.id,
                sender_type="seller",
                sender_id=seller.telegram_id,
                message_text=f"[File: {document_name or 'result'}]",
                files=[{"file_id": document_file_id, "file_name": document_name or "result", "media_type": media_type or "document"}],
            )
        )

    if not order.pending_credited_at:
        await LedgerService.create_seller_hold(
            session,
            seller_id=seller.id,
            amount=Decimal(str(order.price_for_seller)),
            order_id=order.id,
            effective_at=getattr(order, "auto_complete_at", None),
            description=f"Seller escrow hold for order #{order.id}",
        )
        order.pending_credited_at = datetime.now(timezone.utc)

    if not was_completed:
        seller.total_orders += 1

    _sync_bank_stock_flags(bank)

    await session.commit()
    return bank


async def notify_buyer_order_completed(
    session: AsyncSession,
    order: SellerOrder,
    *,
    result_text: str | None = None,
    document_file_id: str | None = None,
    document_name: str | None = None,
    media_type: str = "document",
) -> bool:
    if not order.mirror_bot_id:
        return False

    mirror_bot = await session.scalar(select(MirrorBot).where(MirrorBot.id == order.mirror_bot_id))
    if not mirror_bot:
        return False

    bank = await session.scalar(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
    bank_name = bank.bank_name if bank else "Bank"
    has_chat = bool(getattr(bank, "has_chat", True))
    policy = get_seller_order_policy(order, bank)
    buyer_bot = get_mirror_bot_instance(mirror_bot.bot_token)
    text = format_buyer_order_ready_text(order, bank_name, has_chat, policy, data_revealed=not policy.requires_reveal_confirmation)

    try:
        if policy.requires_reveal_confirmation:
            await buyer_bot.send_message(
                order.buyer_user_id,
                text,
                parse_mode="HTML",
                reply_markup=await build_buyer_order_reveal_keyboard(session, order, bank),
            )
            return True

        await mark_seller_order_data_revealed(session, order)
        keyboard = await build_buyer_order_actions_keyboard(session, order, bank)
        if document_file_id:
            caption = (
                f"{text}\n\n"
                f"📎 Attached file: {document_name or 'result'}"
            )
            if media_type == "photo":
                await buyer_bot.send_photo(
                    order.buyer_user_id,
                    photo=document_file_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
            else:
                await buyer_bot.send_document(
                    order.buyer_user_id,
                    document=document_file_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
        else:
            if result_text:
                text += f"\n\n<b>Result:</b>\n<code>{result_text}</code>"
            await buyer_bot.send_message(
                order.buyer_user_id,
                text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        return True
    except Exception as exc:
        logger.error("Failed to notify buyer about seller order completion: %s", exc)
        return False


async def confirm_seller_order(
    session: AsyncSession,
    order: SellerOrder,
    *,
    auto: bool = False,
) -> bool:
    if order.status != "completed" or order.check_confirmed_at:
        return False

    order.check_confirmed_at = datetime.now(timezone.utc)
    if not order.settled_at:
        seller = await session.scalar(select(Seller).where(Seller.id == order.seller_id))
        if seller:
            await LedgerService.settle_seller_hold(
                session,
                seller_id=seller.id,
                order_id=order.id,
                fallback_amount=Decimal(str(order.price_for_seller)),
            )
        order.settled_at = datetime.now(timezone.utc)
    await session.commit()

    if order.mirror_bot_id:
        mirror_bot = await session.scalar(select(MirrorBot).where(MirrorBot.id == order.mirror_bot_id))
        if mirror_bot:
            bank = await session.scalar(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
            bank_name = bank.bank_name if bank else "Bank"
            policy = get_seller_order_policy(order, bank)
            window_label = _format_window_label(get_seller_order_effective_window_minutes(order, policy))
            buyer_bot = get_mirror_bot_instance(mirror_bot.bot_token)
            text = (
                "✅ <b>Product confirmed!</b>\n\n"
                f"🏦 {bank_name}\n"
                f"📦 Order #{order.id}\n\n"
                "The product is confirmed. You can find it in your profile."
            )
            if auto:
                text = (
                    "✅ <b>Product confirmed automatically!</b>\n\n"
                    f"🏦 {bank_name}\n"
                    f"📦 Order #{order.id}\n\n"
                    f"{window_label} passed with no return request. You can find the product in your profile."
                )
            try:
                await buyer_bot.send_message(
                    order.buyer_user_id,
                    text,
                    parse_mode="HTML",
                    reply_markup=build_buyer_rating_keyboard(order.id),
                )
            except Exception as exc:
                logger.error("Failed to notify buyer about confirmation: %s", exc)

    return True


async def request_seller_order_return(
    session: AsyncSession,
    order: SellerOrder,
    *,
    reason: str,
    comment: str | None = None,
) -> bool:
    if order.status != "completed" or order.check_confirmed_at:
        return False
    bank = await session.scalar(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
    policy = get_seller_order_policy(order, bank)
    if not policy.allows_return:
        return False
    order.status = "moderation_review"
    order.return_reason = reason
    order.return_reason_comment = comment
    order.return_requested_at = datetime.now(timezone.utc)
    order.admin_notes = f"Buyer requested return: {reason}"
    order.check_expires_at = None
    await LedgerService.dispute_seller_hold(session, order_id=order.id)
    dispute = await session.scalar(select(SellerOrderDispute).where(SellerOrderDispute.order_id == order.id))
    if dispute is None:
        session.add(
            SellerOrderDispute(
                order_id=order.id,
                opened_by=order.buyer_user_id,
                reason=reason,
                description=comment or f"Buyer requested return: {reason}",
                status="open",
            )
        )
    await session.commit()
    try:
        from shared.services.admin_notification_service import AdminNotificationService

        bank = await session.scalar(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
        await AdminNotificationService.notify_admin_action(
            "SELLER ORDER RETURN REQUEST",
            [
                f"📦 Order: #{order.id}",
                f"🏦 Bank: {bank.bank_name if bank else 'Bank'}",
                f"↩️ Reason: <b>{reason}</b>",
            ],
            event_type="seller_order_return_requested",
            urgent=True,
        )
    except Exception as exc:
        logger.error("Failed to notify admins about return request: %s", exc)

    if order.mirror_bot_id:
        mirror_bot = await session.scalar(select(MirrorBot).where(MirrorBot.id == order.mirror_bot_id))
        if mirror_bot:
            bank = await session.scalar(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
            bank_name = bank.bank_name if bank else "Bank"
            buyer_bot = get_mirror_bot_instance(mirror_bot.bot_token)
            try:
                await buyer_bot.send_message(
                    order.buyer_user_id,
                    (
                        "⏳ <b>Return request sent to moderation.</b>\n\n"
                        f"🏦 {bank_name}\n"
                        f"📦 Order #{order.id}\n\n"
                        f"Reason: <b>{reason}</b>\n"
                        "Support/moderation will review your request."
                    ),
                    parse_mode="HTML",
                )
            except Exception as exc:
                logger.error("Failed to notify buyer about return: %s", exc)

    return True


async def save_seller_order_rating(
    session: AsyncSession,
    order: SellerOrder,
    *,
    rating: str,
    reason: str | None = None,
) -> bool:
    if rating not in {"like", "dislike"}:
        return False
    if order.feedback_status:
        return False
    order.check_confirmed_at = order.check_confirmed_at or datetime.now(timezone.utc)
    order.feedback_status = "liked" if rating == "like" else "disliked"
    order.feedback_at = datetime.now(timezone.utc)
    order.buyer_rating = rating
    order.buyer_rating_at = datetime.now(timezone.utc)
    order.buyer_rating_reason = reason
    seller = await session.scalar(select(Seller).where(Seller.id == order.seller_id))
    if seller:
        if not order.settled_at:
            await LedgerService.settle_seller_hold(
                session,
                seller_id=seller.id,
                order_id=order.id,
                fallback_amount=Decimal(str(order.price_for_seller)),
            )
            order.settled_at = datetime.now(timezone.utc)
        if rating == "like":
            seller.likes_count = int(getattr(seller, "likes_count", 0) or 0) + 1
        else:
            seller.dislikes_count = int(getattr(seller, "dislikes_count", 0) or 0) + 1
    await session.commit()
    NocoDBService.log_event(
        event_type="buyer_rating_submitted",
        actor_type="buyer",
        actor_id=order.buyer_user_id,
        target_type="seller_order",
        target_id=order.id,
        status=rating,
        payload={
            "seller_id": order.seller_id,
            "reason": reason,
            "price_for_seller": float(order.price_for_seller),
            "price_for_buyer": float(order.price_for_buyer),
        },
        timestamp=order.buyer_rating_at,
    )
    return True


async def auto_confirm_expired_orders(session: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(SellerOrder).where(
            and_(
                SellerOrder.status == "completed",
                SellerOrder.check_confirmed_at.is_(None),
                SellerOrder.check_expires_at.is_not(None),
                SellerOrder.check_expires_at <= now,
            )
        )
    )
    orders = list(result.scalars().all())
    count = 0
    for order in orders:
        if await confirm_seller_order(session, order, auto=True):
            count += 1
    return count
