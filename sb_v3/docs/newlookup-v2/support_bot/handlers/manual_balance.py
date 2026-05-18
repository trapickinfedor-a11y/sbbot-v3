from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import User
from shared.services.admin_audit_service import log_admin_action
from shared.services.admin_notification_service import AdminNotificationService
from shared.services.ledger_service import LedgerService
from support_bot.services.access_service import SupportBotActor

router = Router(name="manual_balance")


class ManualBalanceStates(StatesGroup):
    waiting_reason = State()


def _can_add_balance(actor: SupportBotActor | None) -> bool:
    return bool(actor and actor.can_add_balance)


@router.message(Command("add_balance"))
async def add_balance_start(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _can_add_balance(support_bot_actor):
        await message.answer("❌ You do not have permission to add balance.")
        return

    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /add_balance <user_id> <amount>")
        return

    try:
        user_id = int(parts[1])
    except ValueError:
        await message.answer("User ID must be a number.")
        return

    try:
        amount = Decimal(parts[2])
    except InvalidOperation:
        await message.answer("Amount must be a valid number.")
        return

    amount = amount.quantize(Decimal("0.01"))
    if amount <= 0:
        await message.answer("Amount must be greater than zero.")
        return

    user = await session.scalar(select(User).where(User.user_id == user_id))
    if not user:
        await message.answer("User not found.")
        return

    await state.set_state(ManualBalanceStates.waiting_reason)
    await state.update_data(
        user_id=user.user_id,
        amount=str(amount),
    )
    await message.answer(
        "Пожалуйста, укажите причину пополнения\n\n"
        f"User: <code>{user.user_id}</code>\n"
        f"Amount: <b>${amount:.2f}</b>\n\n"
        "Use /cancel to abort."
    )


@router.message(Command("cancel"), ManualBalanceStates.waiting_reason)
async def add_balance_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Manual balance top-up cancelled.")


@router.message(ManualBalanceStates.waiting_reason, F.text)
async def add_balance_finish(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    support_bot_actor: SupportBotActor | None = None,
):
    if not _can_add_balance(support_bot_actor):
        await state.clear()
        await message.answer("❌ You do not have permission to add balance.")
        return

    reason = (message.text or "").strip()
    if not reason:
        await message.answer("Reason is required. Please enter a non-empty reason.")
        return

    data = await state.get_data()
    await state.clear()

    user_id = int(data["user_id"])
    amount = Decimal(data["amount"])

    user = await session.scalar(select(User).where(User.user_id == user_id))
    if not user:
        await message.answer("User not found.")
        return

    old_balance = Decimal(str(user.balance or 0)).quantize(Decimal("0.01"))
    await LedgerService.credit_user_balance(
        session,
        user_id=user.user_id,
        amount=amount,
        tx_type="admin_adjustment",
        description=f"Manual balance add: {reason}",
        related_entity_type="manual_balance",
        related_entity_id=user.user_id,
    )
    await log_admin_action(
        session,
        admin_id=support_bot_actor.admin_id,
        action="manual_balance_add",
        entity_type="user",
        entity_id=user.user_id,
        details={
            "user_id": user.user_id,
            "amount": float(amount),
            "reason": reason,
            "old_balance": float(old_balance),
            "new_balance": float(user.balance),
            "source": "support_bot",
            "actor_role": support_bot_actor.role,
        },
        actor_label=support_bot_actor.actor_label(),
    )
    await session.commit()
    await AdminNotificationService.notify_balance_update(
        user_id=user.user_id,
        amount=float(amount),
        reason=reason,
        admin_username=support_bot_actor.actor_label(),
    )

    await message.answer(
        "✅ <b>Balance updated.</b>\n\n"
        f"User: <code>{user.user_id}</code>\n"
        f"Added: <b>${amount:.2f}</b>\n"
        f"Old balance: <b>${old_balance:.2f}</b>\n"
        f"New balance: <b>${Decimal(str(user.balance)).quantize(Decimal('0.01')):.2f}</b>\n"
        f"Reason: {reason}"
    )
