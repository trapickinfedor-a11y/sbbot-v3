from __future__ import annotations

"""
Хендлеры для модерации заказов селлеров (approve/reject админом) + просмотр чата
"""

import logging
import os
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import io
import csv

from shared.database.models import SellerOrder, SellerBank, Seller, SellerChat, MirrorBot, SellerOrderDispute
from shared.services.admin_audit_service import log_admin_action
from shared.services.ledger_service import LedgerService
from shared.services.seller_deposit_service import SellerDepositService
from shared.services.nocodb_service import NocoDBService
from shared.services.seller_conversation_service import get_or_create_conversation
from shared.services.seller_order_delivery_service import get_seller_order_policy, get_seller_order_v24_windows
from seller_bot.keyboards.inline import _seller_mini_app_url
from support_bot.config import support_bot_config
from support_bot.services.access_service import SupportAccessService

logger = logging.getLogger(__name__)
router = Router(name="seller_orders_admin")
async def _notify_seller_order_resolution(session: AsyncSession, order: SellerOrder, bank_name: str, *, resolved_for_buyer: bool) -> None:
    try:
        from shared.services.bot_pool import get_seller_bot, get_mirror_bot_instance

        seller = await session.scalar(select(Seller).where(Seller.id == order.seller_id))
        if seller and seller.telegram_id:
            seller_bot = get_seller_bot()
            if seller_bot:
                seller_text = (
                    f"⚠️ <b>Dispute resolved in buyer's favor</b>\n\n"
                    f"Order: <b>#{order.id}</b>\n"
                    f"Product: <b>{bank_name}</b>\n"
                    f"Status: <b>{order.status}</b>"
                    if resolved_for_buyer
                    else
                    f"✅ <b>Dispute resolved in your favor</b>\n\n"
                    f"Order: <b>#{order.id}</b>\n"
                    f"Product: <b>{bank_name}</b>\n"
                    "Buyer dispute was denied and the order remains completed."
                )
                await seller_bot.send_message(seller.telegram_id, seller_text, parse_mode="HTML")

        if order.mirror_bot_id:
            mirror_bot = await session.scalar(select(MirrorBot).where(MirrorBot.id == order.mirror_bot_id))
            if mirror_bot:
                buyer_bot = get_mirror_bot_instance(mirror_bot.bot_token)
                buyer_text = (
                    f"✅ <b>Your dispute was resolved</b>\n\n"
                    f"Order: <b>#{order.id}</b>\n"
                    f"Product: <b>{bank_name}</b>\n"
                    f"Refunded: <b>${order.price_for_buyer:.2f}</b>"
                    if resolved_for_buyer
                    else
                    f"❌ <b>Your dispute was denied</b>\n\n"
                    f"Order: <b>#{order.id}</b>\n"
                    f"Product: <b>{bank_name}</b>\n"
                    "The order remains completed and the dispute window was restarted."
                )
                await buyer_bot.send_message(order.buyer_user_id, buyer_text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to notify seller-order resolution for order {order.id}: {e}")


class RejectOrderStates(StatesGroup):
    waiting_reason = State()


async def _get_seller_moderation_actor(session: AsyncSession, telegram_id: int):
    if telegram_id in support_bot_config.system_admin_ids:
        return SupportAccessService.get_system_admin_actor(telegram_id)
    actor = await SupportAccessService.get_admin_actor(session, telegram_id)
    if actor and actor.can_moderate_sellers:
        return actor
    return None


# ============================================
# ADMIN: VIEW CHAT HISTORY
# ============================================

@router.callback_query(F.data.startswith("admin_view_chat:"))
async def admin_view_chat(callback: CallbackQuery, session: AsyncSession, **kwargs):
    """Админ просматривает переписку по заказу"""
    actor = await _get_seller_moderation_actor(session, callback.from_user.id)
    if not actor:
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    order_id = int(callback.data.split(":")[1])
    
    order_result = await session.execute(
        select(SellerOrder).where(SellerOrder.id == order_id)
    )
    order = order_result.scalar_one_or_none()
    if not order:
        await callback.answer("Order not found", show_alert=True)
        return
    
    bank_result = await session.execute(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
    bank = bank_result.scalar_one_or_none()
    seller_result = await session.execute(select(Seller).where(Seller.id == order.seller_id))
    seller = seller_result.scalar_one_or_none()
    
    chat_result = await session.execute(
        select(SellerChat).where(
            SellerChat.seller_order_id == order_id
        ).order_by(SellerChat.created_at).limit(50)
    )
    messages = list(chat_result.scalars().all())
    
    text = (
        f"💬 <b>Chat Log - Order #{order_id}</b>\n"
        f"🏦 Bank: {bank.bank_name if bank else '?'}\n"
        f"🏪 Seller: {seller.display_name if seller else '?'}\n"
        f"📊 Status: {order.status}\n"
        f"{'─' * 30}\n\n"
    )
    
    if not messages:
        text += "<i>No messages in this chat.</i>"
    else:
        for msg in messages:
            sender = {
                "buyer": "👤 Buyer",
                "seller": "🏪 Seller",
                "admin": "👑 Admin"
            }.get(msg.sender_type, "?")
            time_str = msg.created_at.strftime("%d.%m %H:%M")
            content = msg.message_text or "[file]"
            if msg.files:
                content += f" 📎({len(msg.files)} files)"
            text += f"<b>{sender}</b> [{time_str}]:\n{content}\n\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh", callback_data=f"admin_view_chat:{order_id}")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"admin_order_detail:{order_id}")]
    ])
    
    # Telegram has 4096 char limit, truncate if needed
    if len(text) > 4000:
        text = text[:3950] + "\n\n<i>... truncated (too many messages)</i>"
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_order_detail:"))
async def admin_order_detail(callback: CallbackQuery, session: AsyncSession, **kwargs):
    """Детали заказа с кнопкой просмотра чата"""
    actor = await _get_seller_moderation_actor(session, callback.from_user.id)
    if not actor:
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    order_id = int(callback.data.split(":")[1])
    
    order_result = await session.execute(
        select(SellerOrder).where(SellerOrder.id == order_id)
    )
    order = order_result.scalar_one_or_none()
    if not order:
        await callback.answer("Order not found", show_alert=True)
        return
    
    bank_result = await session.execute(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
    bank = bank_result.scalar_one_or_none()
    seller_result = await session.execute(select(Seller).where(Seller.id == order.seller_id))
    seller = seller_result.scalar_one_or_none()
    
    # Count chat messages
    msg_count_result = await session.execute(
        select(func.count(SellerChat.id)).where(SellerChat.seller_order_id == order_id)
    )
    msg_count = msg_count_result.scalar() or 0
    
    status_map = {
        "pending_admin": "⏳ Pending",
        "approved": "🟡 Approved",
        "in_progress": "🔵 In Progress",
        "completed": "✅ Completed",
        "rejected": "❌ Rejected",
        "cancelled": "⚪ Cancelled",
        "moderation_review": "🛡 Moderation Review",
    }
    
    text = (
        f"📦 <b>Seller Order #{order.id}</b>\n\n"
        f"🏦 Bank: <b>{bank.bank_name if bank else '?'}</b>\n"
        f"🏪 Seller: {seller.display_name if seller else '?'} (@{seller.username or 'N/A'})\n"
        f"📊 Status: {status_map.get(order.status, order.status)}\n"
        f"💰 Buyer pays: <b>${order.price_for_buyer:.2f}</b>\n"
        f"💰 Seller gets: <b>${order.price_for_seller:.2f}</b>\n"
        f"💰 Your margin: <b>${(order.price_for_buyer - order.price_for_seller):.2f}</b>\n"
        f"🔢 Quantity: {order.quantity}\n"
        f"💬 Messages: {msg_count}\n"
        f"📅 Created: {order.created_at.strftime('%Y-%m-%d %H:%M')}\n"
    )
    
    if order.admin_approved_at:
        text += f"✅ Approved: {order.admin_approved_at.strftime('%Y-%m-%d %H:%M')}\n"
    if order.completed_at:
        text += f"🏁 Completed: {order.completed_at.strftime('%Y-%m-%d %H:%M')}\n"
    if getattr(order, "return_reason", None):
        text += f"↩️ Return reason: <b>{order.return_reason}</b>\n"
    if getattr(order, "buyer_rating", None):
        text += f"⭐ Buyer rating: <b>{order.buyer_rating}</b>\n"
    
    buttons = []
    if msg_count > 0:
        buttons.append([InlineKeyboardButton(text=f"💬 View Chat ({msg_count} msgs)", callback_data=f"admin_view_chat:{order_id}")])
    
    if order.status == "pending_admin":
        buttons.append([
            InlineKeyboardButton(text="✅ Approve", callback_data=f"admin_approve_order:{order_id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"admin_reject_order:{order_id}")
        ])
    if order.status == "moderation_review":
        buttons.append([
            InlineKeyboardButton(text="💸 Approve Refund", callback_data=f"admin_refund_order:{order_id}"),
            InlineKeyboardButton(text="✅ Deny Return", callback_data=f"admin_deny_return:{order_id}"),
        ])
    if seller and getattr(seller, "access_status", "") != "banned":
        buttons.append([
            InlineKeyboardButton(text="🚫 Ban Seller for Leak", callback_data=f"admin_ban_seller_leak:{order_id}")
        ])
    
    buttons.append([InlineKeyboardButton(text="⬅️ Back to Orders", callback_data="admin_seller_orders_list")])
    
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    await callback.answer()


@router.message(Command("seller_orders"))
async def cmd_seller_orders(message: Message, session: AsyncSession, **kwargs):
    """Команда для просмотра seller-заказов (только админ)"""
    if message.from_user.id not in support_bot_config.system_admin_ids:
        return
    
    result = await session.execute(
        select(SellerOrder).order_by(SellerOrder.created_at.desc()).limit(15)
    )
    orders = list(result.scalars().all())
    
    if not orders:
        await message.answer("📦 No seller orders yet.")
        return
    
    buttons = []
    for order in orders:
        status_icon = {
            "pending_admin": "⏳", "approved": "🟡", "in_progress": "🔵",
            "completed": "✅", "rejected": "❌", "cancelled": "⚪", "moderation_review": "🛡"
        }.get(order.status, "❓")
        
        bank_result = await session.execute(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
        bank = bank_result.scalar_one_or_none()
        bank_name = bank.bank_name[:20] if bank else "?"
        
        buttons.append([InlineKeyboardButton(
            text=f"{status_icon} #{order.id} | {bank_name} | ${order.price_for_buyer:.0f}",
            callback_data=f"admin_order_detail:{order.id}"
        )])
    
    await message.answer(
        "📦 <b>Seller Orders</b> (last 15)\n\n"
        "Tap an order to see details and chat:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_seller_orders_list")
async def admin_seller_orders_list_cb(callback: CallbackQuery, session: AsyncSession, **kwargs):
    if callback.from_user.id not in support_bot_config.system_admin_ids:
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    result = await session.execute(
        select(SellerOrder).order_by(SellerOrder.created_at.desc()).limit(15)
    )
    orders = list(result.scalars().all())
    
    if not orders:
        await callback.message.edit_text("📦 No seller orders yet.")
        await callback.answer()
        return
    
    buttons = []
    for order in orders:
        status_icon = {
            "pending_admin": "⏳", "approved": "🟡", "in_progress": "🔵",
            "completed": "✅", "rejected": "❌", "cancelled": "⚪"
        }.get(order.status, "❓")
        
        bank_result = await session.execute(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
        bank = bank_result.scalar_one_or_none()
        bank_name = bank.bank_name[:20] if bank else "?"
        
        buttons.append([InlineKeyboardButton(
            text=f"{status_icon} #{order.id} | {bank_name} | ${order.price_for_buyer:.0f}",
            callback_data=f"admin_order_detail:{order.id}"
        )])
    
    await callback.message.edit_text(
        "📦 <b>Seller Orders</b> (last 15)\n\nTap an order to see details and chat:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await callback.answer()


# ============================================
# ANALYTICS: REPORTS via Telegram files
# ============================================

@router.message(Command("seller_report"))
async def cmd_seller_report(message: Message, session: AsyncSession, **kwargs):
    """Отчет по доходам от seller-заказов. /seller_report или /seller_report 7 (дней)"""
    if message.from_user.id not in support_bot_config.system_admin_ids:
        return
    
    # Parse days argument
    args = message.text.split()
    days = 7
    if len(args) > 1:
        try:
            days = int(args[1])
        except ValueError:
            pass
    
    since = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Completed orders in period
    result = await session.execute(
        select(SellerOrder).where(
            and_(
                SellerOrder.created_at >= since,
                SellerOrder.status == "completed"
            )
        ).order_by(SellerOrder.completed_at)
    )
    completed = list(result.scalars().all())
    
    # All orders in period
    all_result = await session.execute(
        select(SellerOrder).where(SellerOrder.created_at >= since)
    )
    all_orders = list(all_result.scalars().all())
    
    total_revenue = sum(o.price_for_buyer for o in completed)
    total_cost = sum(o.price_for_seller for o in completed)
    total_margin = total_revenue - total_cost
    
    pending_count = sum(1 for o in all_orders if o.status == "pending_admin")
    approved_count = sum(1 for o in all_orders if o.status in ("approved", "in_progress"))
    completed_count = len(completed)
    rejected_count = sum(1 for o in all_orders if o.status == "rejected")
    
    # Revenue by day
    daily = {}
    for o in completed:
        day = (o.completed_at or o.created_at).strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"revenue": Decimal("0"), "margin": Decimal("0"), "count": 0}
        daily[day]["revenue"] += o.price_for_buyer
        daily[day]["margin"] += (o.price_for_buyer - o.price_for_seller)
        daily[day]["count"] += 1
    
    # Revenue by seller
    seller_stats = {}
    for o in completed:
        sid = o.seller_id
        if sid not in seller_stats:
            seller_stats[sid] = {"revenue": Decimal("0"), "margin": Decimal("0"), "count": 0}
        seller_stats[sid]["revenue"] += o.price_for_buyer
        seller_stats[sid]["margin"] += (o.price_for_buyer - o.price_for_seller)
        seller_stats[sid]["count"] += 1
    
    # Telegram message
    text = (
        f"📊 <b>Seller Report ({days} days)</b>\n"
        f"📅 {since.strftime('%Y-%m-%d')} → {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n"
        f"📦 <b>Orders:</b>\n"
        f"   ✅ Completed: {completed_count}\n"
        f"   ⏳ Pending: {pending_count}\n"
        f"   🟡 Active: {approved_count}\n"
        f"   ❌ Rejected: {rejected_count}\n"
        f"   📊 Total: {len(all_orders)}\n\n"
        f"💰 <b>Revenue:</b>\n"
        f"   Buyer paid: <b>${total_revenue:.2f}</b>\n"
        f"   Seller cost: ${total_cost:.2f}\n"
        f"   📈 Your margin: <b>${total_margin:.2f}</b>\n\n"
    )
    
    if daily:
        text += "📅 <b>By Day:</b>\n"
        for day in sorted(daily.keys()):
            d = daily[day]
            text += f"   {day}: {d['count']} orders, ${d['revenue']:.2f} rev, ${d['margin']:.2f} margin\n"
        text += "\n"
    
    # Get seller names
    if seller_stats:
        text += "🏪 <b>By Seller:</b>\n"
        for sid, stats in seller_stats.items():
            s_result = await session.execute(select(Seller).where(Seller.id == sid))
            s = s_result.scalar_one_or_none()
            name = s.display_name if s else f"#{sid}"
            text += f"   {name}: {stats['count']} orders, ${stats['margin']:.2f} margin\n"
    
    await message.answer(text, parse_mode="HTML")
    
    # Generate CSV file
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(["Order ID", "Date", "Bank", "Seller", "Buyer ID", "Buyer Price", "Seller Price", "Margin", "Status"])
    
    for o in all_orders:
        bank_r = await session.execute(select(SellerBank).where(SellerBank.id == o.seller_bank_id))
        bank = bank_r.scalar_one_or_none()
        seller_r = await session.execute(select(Seller).where(Seller.id == o.seller_id))
        seller = seller_r.scalar_one_or_none()
        
        writer.writerow([
            o.id,
            o.created_at.strftime("%Y-%m-%d %H:%M"),
            bank.bank_name if bank else "?",
            seller.display_name if seller else "?",
            o.buyer_user_id,
            f"{o.price_for_buyer:.2f}",
            f"{o.price_for_seller:.2f}",
            f"{(o.price_for_buyer - o.price_for_seller):.2f}",
            o.status
        ])
    
    csv_bytes = csv_buffer.getvalue().encode("utf-8")
    csv_buffer.close()
    
    from aiogram.types import BufferedInputFile
    file = BufferedInputFile(
        csv_bytes,
        filename=f"seller_report_{days}d_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    )
    await message.answer_document(file, caption=f"📎 CSV report for last {days} days")


@router.callback_query(F.data.startswith("admin_approve_order:"))
async def approve_order_handler(callback: CallbackQuery, session: AsyncSession, **kwargs):
    user_id = callback.from_user.id
    if user_id not in support_bot_config.system_admin_ids:
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    order_id = int(callback.data.split(":")[1])
    
    result = await session.execute(
        select(SellerOrder).where(SellerOrder.id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        await callback.answer("Order not found", show_alert=True)
        return
    
    if order.status != "pending_admin":
        await callback.answer(f"Order already {order.status}", show_alert=True)
        return
    
    order.status = "approved"
    order.admin_approved_at = datetime.now(timezone.utc)
    await session.commit()
    NocoDBService.log_event(
        event_type="seller_order_status_changed",
        actor_type="admin",
        actor_id=callback.from_user.id,
        target_type="seller_order",
        target_id=order.id,
        status="approved",
        payload={
            "seller_id": order.seller_id,
            "buyer_user_id": order.buyer_user_id,
            "price_for_buyer": float(order.price_for_buyer),
            "price_for_seller": float(order.price_for_seller),
        },
        timestamp=order.admin_approved_at,
    )
    
    # Get bank and seller info
    bank_result = await session.execute(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
    bank = bank_result.scalar_one_or_none()
    seller_result = await session.execute(select(Seller).where(Seller.id == order.seller_id))
    seller = seller_result.scalar_one_or_none()
    
    bank_name = bank.bank_name if bank else "Unknown"
    seller_name = seller.display_name if seller else "Unknown"
    
    await callback.message.edit_text(
        f"✅ <b>Order #{order.id} APPROVED</b>\n\n"
        f"🏦 Bank: {bank_name}\n"
        f"🏪 Seller: {seller_name}\n"
        f"💰 Buyer price: ${order.price_for_buyer:.2f}\n"
        f"💰 Seller price: ${order.price_for_seller:.2f}\n"
        f"📅 Approved: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
    )
    
    if seller:
        try:
            from shared.services.bot_pool import get_seller_bot
            seller_bot = get_seller_bot()
            if seller_bot:
                conv = await get_or_create_conversation(session, order.seller_id, order.buyer_user_id, order.mirror_bot_id)
                mini_app_url = _seller_mini_app_url(conv.id if conv else None)
                await seller_bot.send_message(
                    seller.telegram_id,
                    f"📦 <b>New Order!</b>\n\n"
                    f"🏦 Bank: <b>{bank_name}</b>\n"
                    f"💰 Your earnings: <b>${order.price_for_seller:.2f}</b>\n"
                    f"🔢 Quantity: {order.quantity}\n"
                    f"📦 Order ID: #{order.id}\n\n"
                    f"Please complete this order ASAP.",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="📦 View Order", callback_data=f"seller_order:{order.id}")],
                        *(
                            [[InlineKeyboardButton(text="💬 Chat with Buyer", callback_data=f"seller_chat:{order.id}")]]
                            if bank and getattr(bank, "has_chat", True) else []
                        ),
                        *(
                            [[InlineKeyboardButton(text="🖥 Open Mini App", web_app=WebAppInfo(url=mini_app_url))]]
                            if mini_app_url and bank and getattr(bank, "has_chat", True) else []
                        ),
                    ])
                )
        except Exception as e:
            logger.error(f"Failed to notify seller: {e}")
    
    # Notify buyer that order was approved
    if order.mirror_bot_id:
        try:
            bot_result = await session.execute(
                select(MirrorBot).where(MirrorBot.id == order.mirror_bot_id)
            )
            mirror_bot = bot_result.scalar_one_or_none()
            if mirror_bot:
                from shared.services.bot_pool import get_mirror_bot_instance
                buyer_bot = get_mirror_bot_instance(mirror_bot.bot_token)
                await buyer_bot.send_message(
                    order.buyer_user_id,
                    f"✅ <b>Your order has been approved!</b>\n\n"
                    f"🏦 {bank_name}\n"
                    f"📦 Order #{order.id}\n\n"
                    f"The seller will process your order soon. You can chat with them from My Bank Orders.",
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Failed to notify buyer about approval: {e}")
    
    await callback.answer("✅ Order approved!")


@router.callback_query(F.data.startswith("admin_ban_seller_leak:"))
async def admin_ban_seller_leak_handler(callback: CallbackQuery, session: AsyncSession, **kwargs):
    actor = await _get_seller_moderation_actor(session, callback.from_user.id)
    if not actor:
        await callback.answer("❌ Moderator/Admin only", show_alert=True)
        return

    order_id = int(callback.data.split(":")[1])
    order = await session.scalar(select(SellerOrder).where(SellerOrder.id == order_id))
    if not order:
        await callback.answer("Order not found", show_alert=True)
        return

    seller = await session.scalar(select(Seller).where(Seller.id == order.seller_id))
    if not seller:
        await callback.answer("Seller not found", show_alert=True)
        return
    if getattr(seller, "access_status", "") == "banned":
        await callback.answer("Seller already banned", show_alert=True)
        return

    bank = await session.scalar(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
    reason = f"Confirmed data leak on seller order #{order.id}"
    affected = await SellerDepositService.ban_seller(
        session,
        seller,
        actor_id=callback.from_user.id,
        reason=reason,
        source=f"support_bot_order_{order.id}",
        ban_for_leak=True,
    )
    await log_admin_action(
        session,
        admin_id=actor.admin_id,
        action="seller_leak_ban",
        entity_type="seller",
        entity_id=seller.id,
        details={
            "reason": reason,
            "order_id": order.id,
            "bank_name": bank.bank_name if bank else None,
            "affected": affected,
            "deposit_withheld": True,
        },
        actor_label=actor.actor_label(),
    )
    await session.commit()
    NocoDBService.log_event(
        event_type="seller_order_status_changed",
        actor_type="admin",
        actor_id=callback.from_user.id,
        target_type="seller_order",
        target_id=order.id,
        status="rejected",
        payload={
            "seller_id": order.seller_id,
            "price_for_buyer": float(order.price_for_buyer),
            "ban_for_leak": True,
        },
        timestamp=datetime.now(timezone.utc),
    )

    await callback.message.edit_text(
        "🚫 <b>Seller banned for data leak.</b>\n\n"
        f"🏪 Seller: {seller.display_name or seller.username or seller.id}\n"
        f"📦 Order: #{order.id}\n"
        f"🏦 Bank: {bank.bank_name if bank else '-'}\n"
        f"📝 Reason: {reason}\n"
        f"💸 Deposit: withheld\n"
        f"📉 Banks: {affected['banks_disabled']} | CC: {affected['cc_disabled']} | "
        f"NFC: {affected['nfc_disabled']} | OTP: {affected['otp_disabled']} | "
        f"Selfreg CC: {affected['selfreg_cc_disabled']} | Checks: {affected['checks_disabled']} | "
        f"Brute: {affected['brute_disabled']}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back to Orders", callback_data="admin_seller_orders_list")]
        ]),
    )
    await callback.answer("Seller leak-banned", show_alert=True)


@router.callback_query(F.data.startswith("admin_reject_order:"))
async def reject_order_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, **kwargs):
    user_id = callback.from_user.id
    if user_id not in support_bot_config.system_admin_ids:
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    order_id = int(callback.data.split(":")[1])
    
    result = await session.execute(
        select(SellerOrder).where(SellerOrder.id == order_id)
    )
    order = result.scalar_one_or_none()
    
    if not order or order.status != "pending_admin":
        await callback.answer("Cannot reject this order", show_alert=True)
        return
    
    # Reject immediately, refund buyer
    order.status = "rejected"
    order.admin_notes = "Rejected by admin"
    from shared.services.seller_order_delivery_service import release_seller_order_reservation
    await release_seller_order_reservation(session, order)
    
    # Refund buyer balance via BalanceService (creates Transaction record)
    from support_bot.services.balance_service import BalanceService
    from decimal import Decimal
    refund_success = await BalanceService.refund_order(
        session, order.buyer_user_id, Decimal(str(order.price_for_buyer)), order.id, commit=False
    )
    if not refund_success:
        logger.warning(f"Failed to refund order {order.id} to buyer {order.buyer_user_id}")
        await session.rollback()
        await callback.answer("Refund failed, order not rejected", show_alert=True)
        return

    await session.commit()
    
    bank_result = await session.execute(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
    bank = bank_result.scalar_one_or_none()
    bank_name = bank.bank_name if bank else "Unknown"
    
    await callback.message.edit_text(
        f"❌ <b>Order #{order.id} REJECTED</b>\n\n"
        f"🏦 Bank: {bank_name}\n"
        f"💰 Refunded: ${order.price_for_buyer:.2f} to buyer\n"
        f"📅 Rejected: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}"
    )
    
    # Notify buyer about rejection and refund
    if order.mirror_bot_id:
        try:
            bot_result = await session.execute(
                select(MirrorBot).where(MirrorBot.id == order.mirror_bot_id)
            )
            mirror_bot = bot_result.scalar_one_or_none()
            if mirror_bot:
                from shared.services.bot_pool import get_mirror_bot_instance
                buyer_bot = get_mirror_bot_instance(mirror_bot.bot_token)
                await buyer_bot.send_message(
                    order.buyer_user_id,
                    f"❌ <b>Your order has been cancelled</b>\n\n"
                    f"🏦 {bank_name}\n"
                    f"💰 Refunded: <b>${order.price_for_buyer:.2f}</b>\n\n"
                    f"The amount has been returned to your balance.",
                    parse_mode="HTML"
                )
        except Exception as e:
            logger.error(f"Failed to notify buyer about rejection: {e}")
    
    await callback.answer("❌ Order rejected, buyer refunded")


@router.callback_query(F.data.startswith("admin_refund_order:"))
async def admin_refund_order_handler(callback: CallbackQuery, session: AsyncSession, **kwargs):
    if callback.from_user.id not in support_bot_config.system_admin_ids:
        await callback.answer("❌ Admin only", show_alert=True)
        return
    order_id = int(callback.data.split(":")[1])
    order = await session.scalar(select(SellerOrder).where(SellerOrder.id == order_id).with_for_update())
    if not order or order.status != "moderation_review":
        await callback.answer("Cannot refund this order", show_alert=True)
        return

    from shared.services.seller_order_delivery_service import release_seller_order_reservation
    from support_bot.services.balance_service import BalanceService

    order.status = "cancelled"
    order.returned_at = datetime.now(timezone.utc)
    order.admin_notes = f"Refund approved by moderation. Reason: {order.return_reason or '-'}"
    order.check_expires_at = None
    if hasattr(order, "auto_complete_at"):
        order.auto_complete_at = None
    if hasattr(order, "dispute_deadline_at"):
        order.dispute_deadline_at = None
    bank = await session.scalar(select(SellerBank).where(SellerBank.id == order.seller_bank_id))

    dispute = await session.scalar(select(SellerOrderDispute).where(SellerOrderDispute.order_id == order.id))
    if dispute and dispute.status == "open":
        dispute.status = "resolved_buyer"
        dispute.resolution_note = order.admin_notes
        dispute.resolved_by = callback.from_user.id
        dispute.resolved_at = datetime.now(timezone.utc)

    seller = await session.scalar(select(Seller).where(Seller.id == order.seller_id))
    if seller and order.pending_credited_at and not order.settled_at:
        await LedgerService.fail_seller_hold(session, seller_id=seller.id, order_id=order.id)

    await release_seller_order_reservation(session, order)
    refund_success = await BalanceService.refund_order(
        session,
        order.buyer_user_id,
        Decimal(str(order.price_for_buyer)),
        order.id,
        commit=False,
    )
    if not refund_success:
        await session.rollback()
        await callback.answer("Refund failed", show_alert=True)
        return
    await session.commit()
    await _notify_seller_order_resolution(session, order, bank.bank_name if bank else "Bank", resolved_for_buyer=True)
    await callback.answer("Refund approved")
    callback.data = f"admin_order_detail:{order_id}"
    await admin_order_detail(callback, session, **kwargs)


@router.callback_query(F.data.startswith("admin_deny_return:"))
async def admin_deny_return_handler(callback: CallbackQuery, session: AsyncSession, **kwargs):
    if callback.from_user.id not in support_bot_config.system_admin_ids:
        await callback.answer("❌ Admin only", show_alert=True)
        return
    order_id = int(callback.data.split(":")[1])
    order = await session.scalar(select(SellerOrder).where(SellerOrder.id == order_id))
    if not order or order.status != "moderation_review":
        await callback.answer("Cannot update this order", show_alert=True)
        return
    bank = await session.scalar(select(SellerBank).where(SellerBank.id == order.seller_bank_id))
    dispute_window_hours, _ = await get_seller_order_v24_windows(session)
    now = datetime.now(timezone.utc)
    order.status = "completed"
    order.admin_notes = f"Return denied by moderation. Reason: {order.return_reason or '-'}"
    order.check_window_minutes = dispute_window_hours * 60
    order.check_expires_at = now + timedelta(hours=dispute_window_hours)
    if hasattr(order, "auto_complete_at"):
        order.auto_complete_at = now + timedelta(hours=dispute_window_hours)
    if hasattr(order, "dispute_deadline_at"):
        order.dispute_deadline_at = now + timedelta(hours=dispute_window_hours)
    dispute = await session.scalar(select(SellerOrderDispute).where(SellerOrderDispute.order_id == order.id))
    if dispute and dispute.status == "open":
        dispute.status = "resolved_seller"
        dispute.resolution_note = order.admin_notes
        dispute.resolved_by = callback.from_user.id
        dispute.resolved_at = now
    await session.commit()
    await _notify_seller_order_resolution(session, order, bank.bank_name if bank else "Bank", resolved_for_buyer=False)
    await callback.answer("Return denied")
    callback.data = f"admin_order_detail:{order_id}"
    await admin_order_detail(callback, session, **kwargs)
