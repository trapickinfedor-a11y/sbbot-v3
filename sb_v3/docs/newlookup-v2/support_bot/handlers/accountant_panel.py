from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import (
    AdminAuditLog,
    Marketer,
    MarketerWithdrawal,
    Seller,
    SellerDepositPayment,
    SellerWithdrawal,
    Transaction,
    Worker,
    WorkerWithdrawal,
)
from shared.services.ledger_projection_service import LedgerProjectionService
from shared.services.admin_audit_service import log_admin_action
from shared.services.admin_notification_service import AdminNotificationService
from shared.services.ledger_service import LedgerService
from shared.services.marketer_activity_log import log_marketer_activity
from shared.services.marketer_monitoring_service import (
    build_marketer_withdrawal_block_reason,
    evaluate_marketer_withdrawal_risk,
    notify_marketer_withdrawal_blocked,
)
from support_bot.services.access_service import SupportBotActor

router = Router(name="accountant_panel")

SELLER_BOT_TOKEN = os.getenv("SELLER_BOT_TOKEN", "").strip()
MARKETER_BOT_TOKEN = os.getenv("MARKETER_BOT_TOKEN", "").strip()
SUPPORT_BOT_TOKEN = os.getenv("SUPPORT_BOT_TOKEN", "").strip()


def _accountant_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💸 Seller Withdrawals", callback_data="acct_seller_withdrawals")],
            [InlineKeyboardButton(text="📣 Marketer Withdrawals", callback_data="acct_marketer_withdrawals")],
            [InlineKeyboardButton(text="👷 Worker Withdrawals", callback_data="acct_worker_withdrawals")],
            [InlineKeyboardButton(text="💰 Deposits & Flows", callback_data="acct_recent_flows")],
            [InlineKeyboardButton(text="🧾 Manual Top-up Audit", callback_data="acct_manual_audit")],
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")],
        ]
    )


def _back_accountant_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="accountant_menu")]]
    )


def _seller_task_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Approve", callback_data=f"acct_seller_approve:{task_id}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"acct_seller_reject:{task_id}"),
            ],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="acct_seller_withdrawals")],
        ]
    )


def _marketer_withdrawal_keyboard(withdrawal_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Approve", callback_data=f"acct_marketer_approve:{withdrawal_id}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"acct_marketer_reject:{withdrawal_id}"),
            ],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="acct_marketer_withdrawals")],
        ]
    )


def _worker_withdrawal_keyboard(withdrawal_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Approve", callback_data=f"acct_worker_approve:{withdrawal_id}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"acct_worker_reject:{withdrawal_id}"),
            ],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="acct_worker_withdrawals")],
        ]
    )


def _ensure_accountant(actor: SupportBotActor | None) -> bool:
    return bool(actor and actor.can_manage_finance)


async def _notify_chat(chat_id: int | None, token: str, text: str) -> None:
    if not chat_id or not token:
        return
    bot = Bot(token=token)
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
    finally:
        await bot.session.close()


@router.callback_query(F.data == "accountant_menu")
async def accountant_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _ensure_accountant(support_bot_actor):
        await callback.answer("❌ No accountant access", show_alert=True)
        return

    pending_seller = await session.scalar(
        select(func.count(SellerWithdrawal.id)).where(SellerWithdrawal.status == "pending")
    )
    pending_marketer = await session.scalar(
        select(func.count(MarketerWithdrawal.id)).where(MarketerWithdrawal.status == "pending")
    )
    pending_worker = await session.scalar(
        select(func.count(WorkerWithdrawal.id)).where(WorkerWithdrawal.status == "pending")
    )
    recent_topups = await session.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.type == "topup",
            Transaction.created_at >= datetime.utcnow() - timedelta(days=1),
        )
    )
    recent_adjustments = await session.scalar(
        select(func.count(AdminAuditLog.id)).where(
            AdminAuditLog.action.in_(["manual_balance_add", "user_balance_update"]),
            AdminAuditLog.created_at >= datetime.utcnow() - timedelta(days=7),
        )
    )

    text = (
        "💼 <b>Accountant Panel</b>\n\n"
        f"• Pending seller withdrawals: <b>{int(pending_seller or 0)}</b>\n"
        f"• Pending marketer withdrawals: <b>{int(pending_marketer or 0)}</b>\n"
        f"• Pending worker withdrawals: <b>{int(pending_worker or 0)}</b>\n"
        f"• Top-ups last 24h: <b>${float(recent_topups or 0):.2f}</b>\n"
        f"• Manual top-up actions last 7d: <b>{int(recent_adjustments or 0)}</b>"
    )
    await callback.message.edit_text(text, reply_markup=_accountant_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "acct_seller_withdrawals")
async def seller_withdrawals_list(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _ensure_accountant(support_bot_actor):
        await callback.answer("❌ No accountant access", show_alert=True)
        return

    rows = (
        await session.execute(
            select(SellerWithdrawal)
            .where(SellerWithdrawal.status == "pending")
            .order_by(SellerWithdrawal.created_at.desc())
            .limit(15)
        )
    ).scalars().all()

    if not rows:
        await callback.message.edit_text(
            "💸 <b>Seller Withdrawals</b>\n\nNo pending requests.",
            reply_markup=_back_accountant_keyboard(),
        )
        await callback.answer()
        return

    buttons: list[list[InlineKeyboardButton]] = []
    lines = ["💸 <b>Seller Withdrawals</b>\n"]
    for withdrawal in rows:
        seller = await session.get(Seller, withdrawal.seller_id)
        seller_name = seller.display_name or seller.username or f"Seller #{withdrawal.seller_id}" if seller else f"Seller #{withdrawal.seller_id}"
        lines.append(f"• #{withdrawal.id} {seller_name} - ${float(withdrawal.amount):.2f}")
        buttons.append([InlineKeyboardButton(text=f"#{withdrawal.id} {seller_name}", callback_data=f"acct_seller_detail:{withdrawal.id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="accountant_menu")])
    await callback.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("acct_seller_detail:"))
async def seller_withdrawal_detail(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _ensure_accountant(support_bot_actor):
        await callback.answer("❌ No accountant access", show_alert=True)
        return

    task_id = int(callback.data.split(":")[1])
    task = await session.get(SellerWithdrawal, task_id)
    if not task:
        await callback.answer("Request not found", show_alert=True)
        return

    seller = await session.get(Seller, task.seller_id)
    seller_name = seller.display_name or seller.username or f"Seller #{task.seller_id}" if seller else f"Seller #{task.seller_id}"
    projection = await LedgerProjectionService.get_seller_projection(session, task.seller_id) if seller else None
    balance = float(projection["withdrawable_balance"]) if projection else 0.0
    text = (
        "💸 <b>Seller Withdrawal</b>\n\n"
        f"Request: <b>#{task.id}</b>\n"
        f"Seller: <b>{seller_name}</b>\n"
        f"Amount: <b>${float(task.amount):.2f}</b>\n"
        f"Withdrawable balance: <b>${balance:.2f}</b>\n"
        f"Requisites: {task.requisites or 'Not provided'}\n"
        f"Created: {task.created_at.strftime('%Y-%m-%d %H:%M') if task.created_at else '-'}"
    )
    await callback.message.edit_text(text, reply_markup=_seller_task_keyboard(task.id))
    await callback.answer()


@router.callback_query(F.data.startswith("acct_seller_approve:"))
async def seller_withdrawal_approve(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _ensure_accountant(support_bot_actor):
        await callback.answer("❌ No accountant access", show_alert=True)
        return

    task_id = int(callback.data.split(":")[1])
    task = await session.scalar(
        select(SellerWithdrawal).where(SellerWithdrawal.id == task_id).with_for_update()
    )
    if not task or task.status != "pending":
        await callback.answer("Already processed", show_alert=True)
        return
    seller = await session.get(Seller, task.seller_id)
    if not seller:
        await callback.answer("Seller not found", show_alert=True)
        return
    if not getattr(task, "funds_reserved", False):
        if not await LedgerService.reserve_seller_withdrawal(
            session,
            seller=seller,
            amount=task.amount,
            withdrawal_id=task.id,
        ):
            await callback.answer("Insufficient seller balance", show_alert=True)
            return
        task.funds_reserved = True
    await LedgerService.finalize_seller_withdrawal(
        session,
        seller=seller,
        amount=task.amount,
        withdrawal_id=task.id,
    )
    task.status = "approved"
    task.processed_at = datetime.now(timezone.utc)
    task.processed_by = support_bot_actor.telegram_id
    await log_admin_action(
        session,
        admin_id=support_bot_actor.admin_id,
        action="seller_withdrawal_approve",
        entity_type="seller_withdrawal",
        entity_id=task.id,
        details={
            "seller_id": task.seller_id,
            "amount": float(task.amount),
            "actor_role": support_bot_actor.role,
            "source": "support_bot",
        },
        actor_label=support_bot_actor.actor_label(),
    )
    await session.commit()

    await AdminNotificationService.notify_admin_action(
        "SELLER WITHDRAWAL APPROVED",
        [
            f"💸 <b>Request:</b> #{task_id}",
            f"🏪 <b>Seller ID:</b> #{task.seller_id}",
            f"💵 <b>Amount:</b> ${float(task.amount):.2f}",
            f"🔑 <b>By:</b> {support_bot_actor.actor_label()}",
            "📍 <b>Source:</b> support_bot",
        ],
        event_type="seller_withdrawal_approved",
        urgent=True,
    )
    await _notify_chat(
        seller.telegram_id,
        SELLER_BOT_TOKEN,
        f"✅ <b>Withdrawal approved</b>\n\nAmount: <b>${float(task.amount):.2f}</b>\nStatus: approved",
    )
    await callback.answer("Approved")
    await seller_withdrawals_list(callback, session, support_bot_actor)


@router.callback_query(F.data.startswith("acct_seller_reject:"))
async def seller_withdrawal_reject(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _ensure_accountant(support_bot_actor):
        await callback.answer("❌ No accountant access", show_alert=True)
        return

    task_id = int(callback.data.split(":")[1])
    task = await session.get(SellerWithdrawal, task_id)
    if not task or task.status != "pending":
        await callback.answer("Already processed", show_alert=True)
        return
    seller = await session.get(Seller, task.seller_id)
    if seller and getattr(task, "funds_reserved", False):
        await LedgerService.release_seller_withdrawal_reservation(
            session,
            seller=seller,
            amount=task.amount,
            withdrawal_id=task.id,
        )
    task.status = "rejected"
    task.processed_at = datetime.now(timezone.utc)
    task.processed_by = support_bot_actor.telegram_id
    task.reject_reason = "Rejected by accountant"
    await log_admin_action(
        session,
        admin_id=support_bot_actor.admin_id,
        action="seller_withdrawal_reject",
        entity_type="seller_withdrawal",
        entity_id=task.id,
        details={
            "seller_id": task.seller_id,
            "amount": float(task.amount),
            "reason": task.reject_reason,
            "actor_role": support_bot_actor.role,
            "source": "support_bot",
        },
        actor_label=support_bot_actor.actor_label(),
    )
    await session.commit()

    await AdminNotificationService.notify_admin_action(
        "SELLER WITHDRAWAL REJECTED",
        [
            f"💸 <b>Request:</b> #{task_id}",
            f"🏪 <b>Seller ID:</b> #{task.seller_id}",
            f"💵 <b>Amount:</b> ${float(task.amount):.2f}",
            f"🔑 <b>By:</b> {support_bot_actor.actor_label()}",
            "📍 <b>Source:</b> support_bot",
        ],
        event_type="seller_withdrawal_rejected",
        urgent=True,
    )
    await _notify_chat(
        seller.telegram_id if seller else None,
        SELLER_BOT_TOKEN,
        f"❌ <b>Withdrawal rejected</b>\n\nAmount: <b>${float(task.amount):.2f}</b>\nReason: {task.reject_reason}",
    )
    await callback.answer("Rejected")
    await seller_withdrawals_list(callback, session, support_bot_actor)


@router.callback_query(F.data == "acct_marketer_withdrawals")
async def marketer_withdrawals_list(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _ensure_accountant(support_bot_actor):
        await callback.answer("❌ No accountant access", show_alert=True)
        return

    rows = (
        await session.execute(
            select(MarketerWithdrawal)
            .where(MarketerWithdrawal.status == "pending")
            .order_by(MarketerWithdrawal.created_at.desc())
            .limit(15)
        )
    ).scalars().all()

    if not rows:
        await callback.message.edit_text(
            "📣 <b>Marketer Withdrawals</b>\n\nNo pending requests.",
            reply_markup=_back_accountant_keyboard(),
        )
        await callback.answer()
        return

    buttons: list[list[InlineKeyboardButton]] = []
    lines = ["📣 <b>Marketer Withdrawals</b>\n"]
    for withdrawal in rows:
        marketer = await session.get(Marketer, withdrawal.marketer_id)
        marketer_name = marketer.display_name or marketer.username or f"Marketer #{withdrawal.marketer_id}" if marketer else f"Marketer #{withdrawal.marketer_id}"
        lines.append(f"• #{withdrawal.id} {marketer_name} - ${float(withdrawal.amount):.2f}")
        buttons.append([InlineKeyboardButton(text=f"#{withdrawal.id} {marketer_name}", callback_data=f"acct_marketer_detail:{withdrawal.id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="accountant_menu")])
    await callback.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("acct_marketer_detail:"))
async def marketer_withdrawal_detail(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _ensure_accountant(support_bot_actor):
        await callback.answer("❌ No accountant access", show_alert=True)
        return

    withdrawal_id = int(callback.data.split(":")[1])
    withdrawal = await session.get(MarketerWithdrawal, withdrawal_id)
    if not withdrawal:
        await callback.answer("Request not found", show_alert=True)
        return
    marketer = await session.get(Marketer, withdrawal.marketer_id)
    marketer_name = marketer.display_name or marketer.username or f"Marketer #{withdrawal.marketer_id}" if marketer else f"Marketer #{withdrawal.marketer_id}"
    if marketer:
        projection = await LedgerProjectionService.get_marketer_projection(session, marketer.id)
        balance = float(projection["balance"])
    else:
        balance = 0.0
    text = (
        "📣 <b>Marketer Withdrawal</b>\n\n"
        f"Request: <b>#{withdrawal.id}</b>\n"
        f"Marketer: <b>{marketer_name}</b>\n"
        f"Amount: <b>${float(withdrawal.amount):.2f}</b>\n"
        f"Current balance: <b>${balance:.2f}</b>\n"
        f"Requisites: {withdrawal.requisites or 'Not provided'}\n"
        f"Created: {withdrawal.created_at.strftime('%Y-%m-%d %H:%M') if withdrawal.created_at else '-'}"
    )
    await callback.message.edit_text(text, reply_markup=_marketer_withdrawal_keyboard(withdrawal.id))
    await callback.answer()


@router.callback_query(F.data.startswith("acct_marketer_approve:"))
async def marketer_withdrawal_approve(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _ensure_accountant(support_bot_actor):
        await callback.answer("❌ No accountant access", show_alert=True)
        return

    withdrawal_id = int(callback.data.split(":")[1])
    withdrawal = await session.get(MarketerWithdrawal, withdrawal_id)
    if not withdrawal or withdrawal.status != "pending":
        await callback.answer("Already processed", show_alert=True)
        return
    marketer = await session.get(Marketer, withdrawal.marketer_id)
    if not marketer:
        await callback.answer("Marketer not found", show_alert=True)
        return
    if not getattr(withdrawal, "funds_reserved", False) and float(marketer.balance or 0) < float(withdrawal.amount):
        await callback.answer("Insufficient marketer balance", show_alert=True)
        return

    suspicious_bots = await evaluate_marketer_withdrawal_risk(session, marketer.id)
    if suspicious_bots:
        reason = build_marketer_withdrawal_block_reason(suspicious_bots)
        withdrawal.status = "blocked"
        withdrawal.processed_at = datetime.now(timezone.utc)
        withdrawal.reject_reason = reason
        withdrawal.processed_by = support_bot_actor.telegram_id
        await log_marketer_activity(
            session,
            marketer.id,
            "withdrawal_blocked",
            amount=withdrawal.amount,
            details=reason,
            withdrawal_id=withdrawal.id,
            processed_by=support_bot_actor.telegram_id,
        )
        await log_admin_action(
            session,
            admin_id=support_bot_actor.admin_id,
            action="marketer_withdrawal_block",
            entity_type="marketer_withdrawal",
            entity_id=withdrawal.id,
            details={
                "marketer_id": marketer.id,
                "amount": float(withdrawal.amount),
                "reason": reason,
                "bots": suspicious_bots,
                "source": "support_bot",
                "actor_role": support_bot_actor.role,
            },
            actor_label=support_bot_actor.actor_label(),
        )
        if getattr(withdrawal, "funds_reserved", False):
            await LedgerService.release_marketer_withdrawal_reservation(
                session,
                marketer=marketer,
                amount=withdrawal.amount,
                withdrawal_id=withdrawal.id,
            )
        await session.commit()
        try:
            await notify_marketer_withdrawal_blocked(marketer, withdrawal, suspicious_bots)
        except Exception:
            pass
        await callback.answer("Blocked by risk rules", show_alert=True)
        await marketer_withdrawals_list(callback, session, support_bot_actor)
        return

    if not getattr(withdrawal, "funds_reserved", False):
        if not await LedgerService.reserve_marketer_withdrawal(
            session,
            marketer=marketer,
            amount=withdrawal.amount,
            withdrawal_id=withdrawal.id,
        ):
            await callback.answer("Insufficient marketer balance", show_alert=True)
            return
        withdrawal.funds_reserved = True
    await LedgerService.finalize_marketer_withdrawal(
        session,
        marketer=marketer,
        amount=withdrawal.amount,
        withdrawal_id=withdrawal.id,
    )
    withdrawal.status = "approved"
    withdrawal.processed_at = datetime.now(timezone.utc)
    withdrawal.processed_by = support_bot_actor.telegram_id
    await log_marketer_activity(
        session,
        marketer.id,
        "withdrawal_approved",
        amount=withdrawal.amount,
        details="Approved in support_bot accountant panel",
        withdrawal_id=withdrawal.id,
        processed_by=support_bot_actor.telegram_id,
    )
    await log_admin_action(
        session,
        admin_id=support_bot_actor.admin_id,
        action="marketer_withdrawal_approve",
        entity_type="marketer_withdrawal",
        entity_id=withdrawal.id,
        details={
            "marketer_id": marketer.id,
            "amount": float(withdrawal.amount),
            "source": "support_bot",
            "actor_role": support_bot_actor.role,
        },
        actor_label=support_bot_actor.actor_label(),
    )
    await session.commit()

    await AdminNotificationService.notify_admin_action(
        "MARKETER WITHDRAWAL APPROVED",
        [
            f"📣 <b>Request:</b> #{withdrawal.id}",
            f"🏷 <b>Marketer:</b> {marketer.display_name or marketer.username or marketer.id}",
            f"💵 <b>Amount:</b> ${float(withdrawal.amount):.2f}",
            f"🔑 <b>By:</b> {support_bot_actor.actor_label()}",
            "📍 <b>Source:</b> support_bot",
        ],
        event_type="marketer_withdrawal_approved",
        urgent=True,
    )
    await _notify_chat(
        marketer.telegram_id,
        MARKETER_BOT_TOKEN,
        f"✅ <b>Withdrawal approved</b>\n\nAmount: <b>${float(withdrawal.amount):.2f}</b>\nStatus: approved",
    )
    await callback.answer("Approved")
    await marketer_withdrawals_list(callback, session, support_bot_actor)


@router.callback_query(F.data.startswith("acct_marketer_reject:"))
async def marketer_withdrawal_reject(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _ensure_accountant(support_bot_actor):
        await callback.answer("❌ No accountant access", show_alert=True)
        return

    withdrawal_id = int(callback.data.split(":")[1])
    withdrawal = await session.get(MarketerWithdrawal, withdrawal_id)
    if not withdrawal or withdrawal.status != "pending":
        await callback.answer("Already processed", show_alert=True)
        return
    marketer = await session.get(Marketer, withdrawal.marketer_id)
    if not marketer:
        await callback.answer("Marketer not found", show_alert=True)
        return

    withdrawal.status = "rejected"
    withdrawal.processed_at = datetime.now(timezone.utc)
    withdrawal.processed_by = support_bot_actor.telegram_id
    withdrawal.reject_reason = "Rejected by accountant"
    if getattr(withdrawal, "funds_reserved", False):
        await LedgerService.release_marketer_withdrawal_reservation(
            session,
            marketer=marketer,
            amount=withdrawal.amount,
            withdrawal_id=withdrawal.id,
        )
    await log_marketer_activity(
        session,
        marketer.id,
        "withdrawal_rejected",
        amount=withdrawal.amount,
        details=withdrawal.reject_reason,
        withdrawal_id=withdrawal.id,
        processed_by=support_bot_actor.telegram_id,
    )
    await log_admin_action(
        session,
        admin_id=support_bot_actor.admin_id,
        action="marketer_withdrawal_reject",
        entity_type="marketer_withdrawal",
        entity_id=withdrawal.id,
        details={
            "marketer_id": marketer.id,
            "amount": float(withdrawal.amount),
            "reason": withdrawal.reject_reason,
            "source": "support_bot",
            "actor_role": support_bot_actor.role,
        },
        actor_label=support_bot_actor.actor_label(),
    )
    await session.commit()

    await AdminNotificationService.notify_admin_action(
        "MARKETER WITHDRAWAL REJECTED",
        [
            f"📣 <b>Request:</b> #{withdrawal.id}",
            f"🏷 <b>Marketer:</b> {marketer.display_name or marketer.username or marketer.id}",
            f"💵 <b>Amount:</b> ${float(withdrawal.amount):.2f}",
            f"🔑 <b>By:</b> {support_bot_actor.actor_label()}",
            "📍 <b>Source:</b> support_bot",
        ],
        event_type="marketer_withdrawal_rejected",
        urgent=True,
    )
    await _notify_chat(
        marketer.telegram_id,
        MARKETER_BOT_TOKEN,
        f"❌ <b>Withdrawal rejected</b>\n\nAmount: <b>${float(withdrawal.amount):.2f}</b>\nReason: {withdrawal.reject_reason}",
    )
    await callback.answer("Rejected")
    await marketer_withdrawals_list(callback, session, support_bot_actor)


@router.callback_query(F.data == "acct_worker_withdrawals")
async def worker_withdrawals_list(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _ensure_accountant(support_bot_actor):
        await callback.answer("❌ No accountant access", show_alert=True)
        return

    rows = (
        await session.execute(
            select(WorkerWithdrawal)
            .where(WorkerWithdrawal.status == "pending")
            .order_by(WorkerWithdrawal.created_at.desc())
            .limit(15)
        )
    ).scalars().all()

    if not rows:
        await callback.message.edit_text(
            "👷 <b>Worker Withdrawals</b>\n\nNo pending requests.",
            reply_markup=_back_accountant_keyboard(),
        )
        await callback.answer()
        return

    buttons: list[list[InlineKeyboardButton]] = []
    lines = ["👷 <b>Worker Withdrawals</b>\n"]
    for withdrawal in rows:
        worker = await session.get(Worker, withdrawal.worker_id)
        worker_name = worker.username or f"Worker #{withdrawal.worker_id}" if worker else f"Worker #{withdrawal.worker_id}"
        lines.append(f"• #{withdrawal.id} {worker_name} - ${float(withdrawal.amount):.2f}")
        buttons.append([InlineKeyboardButton(text=f"#{withdrawal.id} {worker_name}", callback_data=f"acct_worker_detail:{withdrawal.id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="accountant_menu")])
    await callback.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@router.callback_query(F.data.startswith("acct_worker_detail:"))
async def worker_withdrawal_detail(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _ensure_accountant(support_bot_actor):
        await callback.answer("❌ No accountant access", show_alert=True)
        return

    withdrawal_id = int(callback.data.split(":")[1])
    withdrawal = await session.get(WorkerWithdrawal, withdrawal_id)
    if not withdrawal:
        await callback.answer("Request not found", show_alert=True)
        return
    worker = await session.get(Worker, withdrawal.worker_id)
    worker_name = worker.username or f"Worker #{withdrawal.worker_id}" if worker else f"Worker #{withdrawal.worker_id}"
    balance = float(worker.balance or 0) if worker else 0.0
    text = (
        "👷 <b>Worker Withdrawal</b>\n\n"
        f"Request: <b>#{withdrawal.id}</b>\n"
        f"Worker: <b>{worker_name}</b>\n"
        f"Amount: <b>${float(withdrawal.amount):.2f}</b>\n"
        f"Current balance: <b>${balance:.2f}</b>\n"
        f"Requisites: {withdrawal.requisites or 'Not provided'}\n"
        f"Created: {withdrawal.created_at.strftime('%Y-%m-%d %H:%M') if withdrawal.created_at else '-'}"
    )
    await callback.message.edit_text(text, reply_markup=_worker_withdrawal_keyboard(withdrawal.id))
    await callback.answer()


@router.callback_query(F.data.startswith("acct_worker_approve:"))
async def worker_withdrawal_approve(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _ensure_accountant(support_bot_actor):
        await callback.answer("❌ No accountant access", show_alert=True)
        return

    withdrawal_id = int(callback.data.split(":")[1])
    withdrawal = await session.get(WorkerWithdrawal, withdrawal_id)
    if not withdrawal or withdrawal.status != "pending":
        await callback.answer("Already processed", show_alert=True)
        return
    worker = await session.get(Worker, withdrawal.worker_id)
    if not worker:
        await callback.answer("Worker not found", show_alert=True)
        return

    if not withdrawal.funds_reserved:
        if not await LedgerService.reserve_worker_withdrawal(
            session,
            worker=worker,
            amount=withdrawal.amount,
            withdrawal_id=withdrawal.id,
        ):
            await callback.answer("Insufficient worker balance", show_alert=True)
            return
        withdrawal.funds_reserved = True
    await LedgerService.finalize_worker_withdrawal(
        session,
        worker=worker,
        amount=withdrawal.amount,
        withdrawal_id=withdrawal.id,
    )
    withdrawal.status = "approved"
    withdrawal.processed_at = datetime.now(timezone.utc)
    withdrawal.processed_by = support_bot_actor.telegram_id
    await log_admin_action(
        session,
        admin_id=support_bot_actor.admin_id,
        action="worker_withdrawal_approve",
        entity_type="worker_withdrawal",
        entity_id=withdrawal.id,
        details={
            "worker_id": withdrawal.worker_id,
            "amount": float(withdrawal.amount),
            "actor_role": support_bot_actor.role,
            "source": "support_bot",
        },
        actor_label=support_bot_actor.actor_label(),
    )
    await session.commit()

    await AdminNotificationService.notify_admin_action(
        "WORKER WITHDRAWAL APPROVED",
        [
            f"👷 <b>Request:</b> #{withdrawal.id}",
            f"🔧 <b>Worker ID:</b> #{withdrawal.worker_id}",
            f"💵 <b>Amount:</b> ${float(withdrawal.amount):.2f}",
            f"🔑 <b>By:</b> {support_bot_actor.actor_label()}",
            "📍 <b>Source:</b> support_bot",
        ],
        event_type="worker_withdrawal_approved",
        urgent=True,
    )
    await _notify_chat(
        worker.telegram_id,
        SUPPORT_BOT_TOKEN,
        f"✅ <b>Withdrawal approved</b>\n\nAmount: <b>${float(withdrawal.amount):.2f}</b>\nStatus: approved",
    )
    await callback.answer("Approved")
    await worker_withdrawals_list(callback, session, support_bot_actor)


@router.callback_query(F.data.startswith("acct_worker_reject:"))
async def worker_withdrawal_reject(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _ensure_accountant(support_bot_actor):
        await callback.answer("❌ No accountant access", show_alert=True)
        return

    withdrawal_id = int(callback.data.split(":")[1])
    withdrawal = await session.get(WorkerWithdrawal, withdrawal_id)
    if not withdrawal or withdrawal.status != "pending":
        await callback.answer("Already processed", show_alert=True)
        return
    worker = await session.get(Worker, withdrawal.worker_id)

    if worker and withdrawal.funds_reserved:
        await LedgerService.release_worker_withdrawal_reservation(
            session,
            worker=worker,
            amount=withdrawal.amount,
            withdrawal_id=withdrawal.id,
        )
    withdrawal.status = "rejected"
    withdrawal.processed_at = datetime.now(timezone.utc)
    withdrawal.processed_by = support_bot_actor.telegram_id
    withdrawal.reject_reason = "Rejected by accountant"
    await log_admin_action(
        session,
        admin_id=support_bot_actor.admin_id,
        action="worker_withdrawal_reject",
        entity_type="worker_withdrawal",
        entity_id=withdrawal.id,
        details={
            "worker_id": withdrawal.worker_id,
            "amount": float(withdrawal.amount),
            "reason": withdrawal.reject_reason,
            "actor_role": support_bot_actor.role,
            "source": "support_bot",
        },
        actor_label=support_bot_actor.actor_label(),
    )
    await session.commit()

    await AdminNotificationService.notify_admin_action(
        "WORKER WITHDRAWAL REJECTED",
        [
            f"👷 <b>Request:</b> #{withdrawal.id}",
            f"🔧 <b>Worker ID:</b> #{withdrawal.worker_id}",
            f"💵 <b>Amount:</b> ${float(withdrawal.amount):.2f}",
            f"🔑 <b>By:</b> {support_bot_actor.actor_label()}",
            "📍 <b>Source:</b> support_bot",
        ],
        event_type="worker_withdrawal_rejected",
        urgent=True,
    )
    await _notify_chat(
        worker.telegram_id if worker else None,
        SUPPORT_BOT_TOKEN,
        f"❌ <b>Withdrawal rejected</b>\n\nAmount: <b>${float(withdrawal.amount):.2f}</b>\nReason: {withdrawal.reject_reason}",
    )
    await callback.answer("Rejected")
    await worker_withdrawals_list(callback, session, support_bot_actor)


@router.callback_query(F.data == "acct_recent_flows")
async def recent_finance_flows(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _ensure_accountant(support_bot_actor):
        await callback.answer("❌ No accountant access", show_alert=True)
        return

    tx_rows = (
        await session.execute(
            select(Transaction).order_by(desc(Transaction.created_at)).limit(10)
        )
    ).scalars().all()
    deposit_rows = (
        await session.execute(
            select(SellerDepositPayment).order_by(desc(SellerDepositPayment.created_at)).limit(10)
        )
    ).scalars().all()
    lines = ["💰 <b>Recent Financial Flows</b>\n", "<b>User transactions</b>"]
    if tx_rows:
        for row in tx_rows:
            lines.append(
                f"• {row.created_at.strftime('%m-%d %H:%M')} | {row.type} | user <code>{row.user_id}</code> | ${float(row.amount):.2f}"
            )
    else:
        lines.append("• No transactions found")
    lines.append("\n<b>Seller deposits</b>")
    if deposit_rows:
        for row in deposit_rows:
            lines.append(
                f"• {row.created_at.strftime('%m-%d %H:%M')} | seller #{row.seller_id} | {row.status} | ${float(row.amount):.2f}"
            )
    else:
        lines.append("• No seller deposits found")
    await callback.message.edit_text("\n".join(lines), reply_markup=_back_accountant_keyboard())
    await callback.answer()


@router.callback_query(F.data == "acct_manual_audit")
async def manual_topup_audit(
    callback: CallbackQuery,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _ensure_accountant(support_bot_actor):
        await callback.answer("❌ No accountant access", show_alert=True)
        return

    rows = (
        await session.execute(
            select(AdminAuditLog)
            .where(AdminAuditLog.action.in_(["manual_balance_add", "user_balance_update"]))
            .order_by(desc(AdminAuditLog.created_at))
            .limit(15)
        )
    ).scalars().all()

    lines = ["🧾 <b>Manual Top-up Audit</b>\n"]
    if not rows:
        lines.append("• No manual top-up actions found")
    for row in rows:
        details = row.details or {}
        amount = details.get("amount")
        reason = details.get("reason") or details.get("description") or "-"
        user_id = details.get("user_id") or row.entity_id or "-"
        lines.append(
            f"• {row.created_at.strftime('%m-%d %H:%M')} | user <code>{user_id}</code> | ${float(amount or 0):.2f} | {reason}"
        )
    await callback.message.edit_text("\n".join(lines), reply_markup=_back_accountant_keyboard())
    await callback.answer()
