"""
Хэндлеры для просмотра информации о пользователе и списания баланса
"""

from decimal import Decimal, InvalidOperation
from typing import Optional

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
import logging

from support_bot.services.worker_service import WorkerService
from support_bot.keyboards.inline import back_to_menu_keyboard
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from support_bot.utils import safe_edit_message, safe_answer_callback
from shared.database.models import User, Order
from shared.services.ledger_service import LedgerService
from support_bot.services.access_service import SupportBotActor

router = Router(name="user_info")
logger = logging.getLogger(__name__)


class UserInfoStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_additional_message = State()
    waiting_for_debit_amount = State()
    waiting_for_debit_reason = State()


def user_id_input_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_user_id")]
    ])


def additional_message_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data=f"cancel_additional_message:{order_id}")]
    ])


def user_actions_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Deduct Balance", callback_data=f"debit_user:{user_id}")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
    ])


def cancel_debit_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_debit")]
    ])


async def _check_balance_permission(callback: CallbackQuery, session: AsyncSession, actor: Optional[SupportBotActor] = None) -> bool:
    if actor and actor.can_add_balance:
        return True
    worker = await WorkerService.get_worker(session, callback.from_user.id)
    if worker and getattr(worker, 'can_check_balance', False):
        return True
    await callback.answer("❌ You don't have access to this feature", show_alert=True)
    return False


@router.callback_query(F.data == "check_user_balance")
async def check_user_balance_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext, support_bot_actor: Optional[SupportBotActor] = None):
    if not await _check_balance_permission(callback, session, support_bot_actor):
        return

    await state.set_state(UserInfoStates.waiting_for_user_id)

    await callback.message.edit_text(
        "🔍 <b>Check User Balance</b>\n\n"
        "Enter the user's Telegram ID:\n\n"
        "Example: <code>123456789</code>",
        reply_markup=user_id_input_keyboard()
    )
    await callback.answer()


@router.message(UserInfoStates.waiting_for_user_id)
async def process_user_id(message: Message, session: AsyncSession, state: FSMContext):
    try:
        user_id = int(message.text.strip())

        stmt = select(User).where(User.user_id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            await message.answer(
                "❌ User not found!\n\n"
                "Please check the ID and try again.",
                reply_markup=user_id_input_keyboard()
            )
            return

        stmt = select(
            func.count(Order.id).label("total"),
            func.sum(case((Order.status == "completed", 1), else_=0)).label("completed"),
            func.sum(case((Order.status == "pending", 1), else_=0)).label("pending"),
            func.sum(case((Order.status == "processing", 1), else_=0)).label("processing")
        ).where(Order.user_id == user_id)

        result = await session.execute(stmt)
        stats = result.first()

        text = f"""👤 <b>USER INFO</b>

🆔 <b>Telegram ID:</b> <code>{user.user_id}</code>
💰 <b>Balance:</b> ${user.balance:.2f}
🌐 <b>Language:</b> {user.language}

📊 <b>Orders Statistics:</b>
   • Total: {stats.total or 0}
   • ✅ Completed: {stats.completed or 0}
   • ⏳ Pending: {stats.pending or 0}
   • 🔄 Processing: {stats.processing or 0}

━━━━━━━━━━━━━━━━━━
📅 <b>Registered:</b> {user.created_at.strftime('%Y-%m-%d %H:%M')}
"""

        if user.referrer_id:
            text += f"\n👥 <b>Referred by:</b> <code>{user.referrer_id}</code>"

        await message.answer(text, reply_markup=user_actions_keyboard(user.user_id))
        await state.clear()

    except ValueError:
        await message.answer(
            "❌ Invalid ID format!\n"
            "Please enter a valid number.",
            reply_markup=user_id_input_keyboard()
        )


@router.callback_query(F.data == "cancel_user_id")
async def cancel_user_id_input(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("❌ User ID input cancelled")
    await callback.message.edit_text(
        "🏠 <b>Support Panel</b>\n\nUse the main menu button to return.",
        reply_markup=back_to_menu_keyboard(),
    )


# ── Deduct Balance ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("debit_user:"))
async def debit_user_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext, support_bot_actor: Optional[SupportBotActor] = None):
    # Workers must never be able to debit user balances — admin/support only.
    if support_bot_actor is not None and support_bot_actor.is_worker:
        await callback.answer("❌ Access denied: workers cannot debit user balances", show_alert=True)
        return
    if not await _check_balance_permission(callback, session, support_bot_actor):
        return

    user_id = int(callback.data.split(":")[1])
    stmt = select(User).where(User.user_id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        await callback.answer("❌ User not found", show_alert=True)
        return

    await state.set_state(UserInfoStates.waiting_for_debit_amount)
    await state.update_data(debit_user_id=user.user_id, debit_user_balance=float(user.balance))

    await callback.message.edit_text(
        f"💸 <b>Deduct Balance</b>\n\n"
        f"User: <code>{user.user_id}</code>\n"
        f"Current balance: <b>${user.balance:.2f}</b>\n\n"
        f"Enter the amount to deduct (USD):",
        reply_markup=cancel_debit_keyboard()
    )
    await callback.answer()


@router.message(UserInfoStates.waiting_for_debit_amount)
async def debit_amount_input(message: Message, state: FSMContext):
    try:
        amount = Decimal(message.text.replace(",", ".").strip()).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        await message.answer("Please enter a valid number (e.g. 10 or 25.50)", reply_markup=cancel_debit_keyboard())
        return

    if amount <= 0:
        await message.answer("Amount must be positive.", reply_markup=cancel_debit_keyboard())
        return

    data = await state.get_data()
    user_balance = Decimal(str(data.get("debit_user_balance", 0)))
    if amount > user_balance:
        await message.answer(
            f"❌ Amount exceeds user balance (${user_balance:.2f}).\n"
            f"Enter a smaller amount.",
            reply_markup=cancel_debit_keyboard()
        )
        return

    await state.update_data(debit_amount=str(amount))
    await state.set_state(UserInfoStates.waiting_for_debit_reason)
    await message.answer(
        f"Amount: <b>${amount:.2f}</b>\n\n"
        f"Enter the reason for deduction:",
        reply_markup=cancel_debit_keyboard()
    )


@router.message(UserInfoStates.waiting_for_debit_reason)
async def debit_reason_input(message: Message, session: AsyncSession, state: FSMContext):
    reason = (message.text or "").strip()
    if not reason:
        await message.answer("Reason is required. Please enter a reason.", reply_markup=cancel_debit_keyboard())
        return

    data = await state.get_data()
    user_id = int(data["debit_user_id"])
    amount = Decimal(data["debit_amount"])

    user = await session.scalar(select(User).where(User.user_id == user_id))
    if not user:
        await message.answer("❌ User not found.")
        await state.clear()
        return

    if Decimal(str(user.balance or 0)) < amount:
        await message.answer("❌ Insufficient user balance. Deduction cancelled.")
        await state.clear()
        return

    worker = await WorkerService.get_worker(session, message.from_user.id)
    worker_label = f"worker:{worker.id}" if worker else f"tg:{message.from_user.id}"

    await LedgerService.debit_user_balance(
        session,
        user_id=user.user_id,
        amount=amount,
        tx_type="worker_deduction",
        description=f"Balance deduction by {worker_label}: {reason}",
        related_entity_type="worker_deduction",
        related_entity_id=user.user_id,
    )
    await session.commit()

    logger.info(f"Worker {worker_label} deducted ${amount} from user {user_id}: {reason}")

    await state.clear()
    await message.answer(
        f"✅ <b>Balance deducted!</b>\n\n"
        f"User: <code>{user_id}</code>\n"
        f"Deducted: <b>${amount:.2f}</b>\n"
        f"Reason: {reason}\n"
        f"New balance: <b>${Decimal(str(user.balance)).quantize(Decimal('0.01')):.2f}</b>",
        reply_markup=back_to_menu_keyboard()
    )


@router.callback_query(F.data == "cancel_debit")
async def cancel_debit(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("❌ Deduction cancelled")
    await callback.message.edit_text(
        "🏠 <b>Support Panel</b>\n\nUse the main menu button to return.",
        reply_markup=back_to_menu_keyboard(),
    )


# ── Send Additional Message ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("send_additional_message:"))
async def send_additional_message_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    order_id = int(callback.data.split(":")[1])

    worker = await WorkerService.get_worker(session, callback.from_user.id)

    from support_bot.services.order_service import OrderService
    order = await OrderService.get_order(session, order_id)

    if not order or order.worker_id != worker.id:
        await callback.answer("❌ Access denied", show_alert=True)
        return

    await state.update_data(order_id=order_id, user_id=order.user_id)
    await state.set_state(UserInfoStates.waiting_for_additional_message)

    await safe_edit_message(
        callback,
        f"💬 <b>Send Additional Message</b>\n\n"
        f"Order: #{order_id}\n"
        f"User: <code>{order.user_id}</code>\n\n"
        f"Enter your message to send to the customer:",
        reply_markup=additional_message_keyboard(order_id)
    )
    await safe_answer_callback(callback)


@router.message(UserInfoStates.waiting_for_additional_message)
async def process_additional_message(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("order_id")
    user_id = data.get("user_id")

    if not order_id or not user_id:
        await message.answer("❌ Error: Order information not found")
        await state.clear()
        return

    try:
        from support_bot.services.worker_notification_service import WorkerNotificationService
        bot = WorkerNotificationService._bot

        await bot.send_message(
            chat_id=user_id,
            text=f"💬 <b>Additional message about order #{order_id}:</b>\n\n{message.text}",
            parse_mode="HTML"
        )

        await message.answer(
            f"✅ <b>Message sent!</b>\n\n"
            f"Your message has been delivered to the customer.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Back to Order", callback_data=f"order_view:{order_id}")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
            ])
        )

        logger.info(f"Additional message sent for order {order_id} to user {user_id}")

    except Exception as e:
        logger.error(f"Failed to send additional message: {e}")
        await message.answer(
            f"❌ Failed to send message!\n"
            f"Error: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Back to Order", callback_data=f"order_view:{order_id}")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")]
            ])
        )

    await state.clear()


@router.callback_query(F.data.startswith("cancel_additional_message:"))
async def cancel_additional_message(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    order_id = int(callback.data.split(":")[1])

    await state.clear()

    from support_bot.handlers.orders import show_order_details
    await show_order_details(callback, session, order_id)
    await callback.answer("❌ Additional message cancelled")
