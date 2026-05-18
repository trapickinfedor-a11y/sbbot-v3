from __future__ import annotations
"""Handler for seller withdrawal requests"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from shared.database.models import Seller, SellerWithdrawal
from shared.services.admin_notification_service import AdminNotificationService
from shared.services.ledger_projection_service import LedgerProjectionService
from shared.services.ledger_service import LedgerService
from seller_bot.keyboards.inline import seller_main_menu
from seller_bot.utils import get_seller_unread_count

logger = logging.getLogger(__name__)
router = Router(name="seller_withdrawal")


class WithdrawalStates(StatesGroup):
    waiting_amount = State()
    waiting_requisites = State()


@router.message(WithdrawalStates.waiting_amount | WithdrawalStates.waiting_requisites, Command("cancel"))
async def withdraw_cancel(message: Message, state: FSMContext, texts, **kwargs):
    await state.clear()
    cancel_text = getattr(texts, "WITHDRAW_CANCELLED", "❌ Withdrawal cancelled.")
    await message.answer(cancel_text)


@router.callback_query(F.data == "seller_withdraw")
async def withdraw_start(callback: CallbackQuery, session: AsyncSession, seller, state: FSMContext, texts, buttons, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    if not seller or not seller_actor or not seller_actor.can_manage_finance():
        await callback.answer(texts.NOT_AUTHORIZED, show_alert=True)
        return
    projection = await LedgerProjectionService.get_seller_projection(session, seller.id)
    withdrawable = float(projection["withdrawable_balance"])
    pending = float(projection["pending_balance"])
    if withdrawable <= 0:
        await callback.answer(texts.WITHDRAW_INSUFFICIENT, show_alert=True)
        return
    await state.set_state(WithdrawalStates.waiting_amount)
    await state.update_data(seller_id=seller.id)
    await callback.message.edit_text(
        texts.WITHDRAW_START.format(withdrawable=withdrawable, pending=pending)
    )
    await callback.answer()


@router.message(WithdrawalStates.waiting_amount, F.text)
async def withdraw_amount(message: Message, session: AsyncSession, seller, state: FSMContext, texts, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    if not seller or not seller_actor or not seller_actor.can_manage_finance():
        return
    try:
        amount = float(message.text.replace(",", ".").strip())
    except ValueError:
        await message.answer(texts.WITHDRAW_ENTER_VALID)
        return
    deposit = float((await LedgerProjectionService.get_seller_projection(session, seller.id))["withdrawable_balance"])
    if amount <= 0:
        await message.answer(texts.WITHDRAW_POSITIVE)
        return
    if amount > deposit:
        await message.answer(texts.WITHDRAW_NOT_ENOUGH.format(balance=deposit))
        return
    await state.update_data(amount=amount)
    await state.set_state(WithdrawalStates.waiting_requisites)
    await message.answer(texts.WITHDRAW_ENTER_DETAILS)


@router.message(WithdrawalStates.waiting_requisites, F.text)
async def withdraw_requisites(message: Message, session: AsyncSession, seller, state: FSMContext, texts, buttons, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    if not seller or not seller_actor or not seller_actor.can_manage_finance():
        return
    data = await state.get_data()
    amount = data.get("amount", 0)
    requisites = (message.text or "").strip() or None
    deposit = float((await LedgerProjectionService.get_seller_projection(session, seller.id))["withdrawable_balance"])
    if amount > deposit:
        await message.answer(texts.WITHDRAW_CANCELLED)
        await state.clear()
        return
    withdrawal_id: int | None = None
    try:
        # Auto-approve withdrawals under $500 (AUTO_WITHDRAWAL_THRESHOLD per spec v24)
        AUTO_WITHDRAWAL_THRESHOLD = 500.0
        trust_score = float(getattr(seller, "trust_score", 100) or 100)
        auto_approve = (
            amount <= AUTO_WITHDRAWAL_THRESHOLD
            and trust_score >= 30
            and not getattr(seller, "is_frozen", False)
        )
        initial_status = "approved" if auto_approve else "pending"

        withdrawal = SellerWithdrawal(
            seller_id=seller.id,
            amount=Decimal(str(amount)),
            requisites=requisites,
            status=initial_status,
        )
        session.add(withdrawal)
        await session.flush()
        withdrawal_id = withdrawal.id
        reserved = await LedgerService.reserve_seller_withdrawal(
            session,
            seller=seller,
            amount=Decimal(str(amount)),
            withdrawal_id=withdrawal.id,
        )
        if not reserved:
            await session.rollback()
            await message.answer(texts.WITHDRAW_CANCELLED)
            await state.clear()
            return
        withdrawal.funds_reserved = True
        if auto_approve:
            await LedgerService.finalize_seller_withdrawal(
                session,
                seller=seller,
                amount=Decimal(str(amount)),
                withdrawal_id=withdrawal.id,
            )
            withdrawal.status = "completed"
        await session.commit()
    except Exception:
        await session.rollback()
        if withdrawal_id is not None:
            try:
                failed = await session.get(SellerWithdrawal, withdrawal_id)
                if failed:
                    failed.funds_reserved = False
                    failed.status = "rejected"
                    failed.reject_reason = "Reservation sync failed"
                    await session.commit()
            except Exception:
                pass
        raise
    await AdminNotificationService.notify_admin_action(
        "SELLER WITHDRAWAL REQUEST",
        [
            f"🏪 <b>Seller:</b> {seller.display_name or seller.username or seller.id} (#{seller.id})",
            f"🆔 <b>Telegram ID:</b> <code>{seller.telegram_id}</code>",
            f"💵 <b>Amount:</b> ${amount:.2f}",
            f"💳 <b>Requisites:</b> {requisites or 'Not provided'}",
        ],
        event_type="seller_withdrawal_requested",
        urgent=True,
    )
    await state.clear()
    unread = await get_seller_unread_count(session, seller.id)
    await message.answer(
        texts.WITHDRAW_CREATED.format(amount=amount),
        reply_markup=seller_main_menu(unread_count=unread, buttons=buttons, actor_role=seller_actor.role)
    )
