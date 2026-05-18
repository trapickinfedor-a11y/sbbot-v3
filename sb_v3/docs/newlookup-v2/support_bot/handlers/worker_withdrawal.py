from __future__ import annotations
"""Handler для заявок на вывод средств и отчётов о расходах воркеров"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from shared.database.models import Worker, WorkerExpenseReport, WorkerWithdrawal
from shared.services.ledger_projection_service import LedgerProjectionService
from shared.services.ledger_service import LedgerService
from support_bot.services.worker_service import WorkerService
from support_bot.keyboards.inline import main_menu_keyboard, profile_keyboard

logger = logging.getLogger(__name__)
router = Router(name="worker_withdrawal")

EXPENSE_CATEGORIES = {
    "proxy": "🌐 Proxy",
    "cards": "💳 Cards",
    "other": "📦 Other",
}

EXPENSE_RULES_TEXT = (
    "📋 <b>Expense Report Rules</b>\n\n"
    "1. Only work-related expenses are accepted\n"
    "2. Attach a screenshot or PDF receipt (required)\n"
    "3. Categories: Proxy, Cards, Other\n"
    "4. Description must explain the purpose of the expense\n"
    "5. Reports without receipts will be rejected\n"
    "6. Admin reviews and approves/rejects each report\n"
)


class WorkerWithdrawalStates(StatesGroup):
    waiting_amount = State()
    waiting_requisites = State()


class WorkerExpenseStates(StatesGroup):
    waiting_amount = State()
    waiting_category = State()
    waiting_description = State()
    waiting_receipt = State()


@router.callback_query(F.data == "worker_withdraw")
async def withdraw_start(callback: CallbackQuery, session: AsyncSession, worker, state: FSMContext, **kwargs):
    if not worker:
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    balance = float((await LedgerProjectionService.get_worker_projection(session, worker.id))["balance"])
    if balance <= 0:
        await callback.answer("Insufficient balance", show_alert=True)
        return
    await state.set_state(WorkerWithdrawalStates.waiting_amount)
    await state.update_data(worker_id=worker.id)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    await callback.message.edit_text(
        f"💸 <b>Withdraw Funds</b>\n\n"
        f"Your balance: <b>${balance:.2f}</b>\n\n"
        f"Enter the amount to withdraw (USD):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_withdrawal")]
        ])
    )
    await callback.answer()


@router.message(WorkerWithdrawalStates.waiting_amount, F.text)
async def withdraw_amount(message: Message, session: AsyncSession, worker, state: FSMContext, **kwargs):
    if not worker:
        return
    try:
        amount = float(message.text.replace(",", ".").strip())
    except ValueError:
        await message.answer("Please enter a valid number (e.g. 50 or 100.50)")
        return
    balance = float((await LedgerProjectionService.get_worker_projection(session, worker.id))["balance"])
    if amount <= 0:
        await message.answer("Amount must be positive.")
        return
    if amount > balance:
        await message.answer(f"Insufficient balance. You have ${balance:.2f}")
        return
    await state.update_data(amount=amount)
    await state.set_state(WorkerWithdrawalStates.waiting_requisites)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    await message.answer(
        "Enter your wallet/payment details (card, crypto address, etc.):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_withdrawal")]
        ])
    )


@router.message(WorkerWithdrawalStates.waiting_requisites, F.text)
async def withdraw_requisites(message: Message, session: AsyncSession, worker, state: FSMContext, **kwargs):
    if not worker:
        return
    data = await state.get_data()
    amount = data.get("amount", 0)
    requisites = (message.text or "").strip() or None
    balance = float((await LedgerProjectionService.get_worker_projection(session, worker.id))["balance"])
    if amount > balance:
        await message.answer("Insufficient balance. Request cancelled.")
        await state.clear()
        return
    withdrawal_id: int | None = None
    try:
        withdrawal = WorkerWithdrawal(
            worker_id=worker.id,
            amount=Decimal(str(amount)),
            requisites=requisites,
            status="pending",
        )
        session.add(withdrawal)
        await session.flush()
        withdrawal_id = withdrawal.id
        reserved = await LedgerService.reserve_worker_withdrawal(
            session,
            worker=worker,
            amount=Decimal(str(amount)),
            withdrawal_id=withdrawal.id,
        )
        if not reserved:
            await session.rollback()
            await message.answer("Insufficient balance. Request cancelled.")
            await state.clear()
            return
        withdrawal.funds_reserved = True
        await session.commit()
    except Exception:
        await session.rollback()
        if withdrawal_id is not None:
            try:
                failed = await session.get(WorkerWithdrawal, withdrawal_id)
                if failed:
                    failed.funds_reserved = False
                    failed.status = "rejected"
                    failed.reject_reason = "Reservation sync failed"
                    await session.commit()
            except Exception:
                pass
        raise
    await state.clear()
    await message.answer(
        f"✅ Withdrawal request created!\n\n"
        f"Amount: ${amount:.2f}\n"
        f"Status: Pending admin approval\n\n"
        f"You will be notified when it is processed.",
        reply_markup=main_menu_keyboard(worker)
    )


@router.callback_query(F.data == "cancel_withdrawal")
async def cancel_withdrawal(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.clear()
    await callback.answer("❌ Withdrawal cancelled")
    await callback.message.edit_text(
        "🏠 Withdrawal cancelled.",
        reply_markup=main_menu_keyboard()
    )


# ========== Expense Reports ==========

def _expense_cancel_kb() -> InlineKeyboardMarkup:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_expense")]
    ])


def _expense_category_kb() -> InlineKeyboardMarkup:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = [[InlineKeyboardButton(text=label, callback_data=f"exp_cat:{key}")] for key, label in EXPENSE_CATEGORIES.items()]
    buttons.append([InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_expense")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "worker_expense_report")
async def expense_report_start(callback: CallbackQuery, session: AsyncSession, worker, state: FSMContext, **kwargs):
    if not worker:
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    await state.set_state(WorkerExpenseStates.waiting_amount)
    await state.update_data(worker_id=worker.id)
    await callback.message.edit_text(
        f"{EXPENSE_RULES_TEXT}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Enter the amount (USD):",
        reply_markup=_expense_cancel_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_expense")
async def cancel_expense(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.clear()
    await callback.answer("❌ Expense report cancelled")
    await callback.message.edit_text(
        "🏠 Expense report cancelled.",
        reply_markup=main_menu_keyboard()
    )


@router.message(WorkerExpenseStates.waiting_amount, F.text)
async def expense_amount(message: Message, session: AsyncSession, worker, state: FSMContext, **kwargs):
    if not worker:
        return
    try:
        amount = float(message.text.replace(",", ".").strip())
    except ValueError:
        await message.answer("Please enter a valid number (e.g. 25.50)", reply_markup=_expense_cancel_kb())
        return
    if amount <= 0:
        await message.answer("Amount must be positive.", reply_markup=_expense_cancel_kb())
        return
    await state.update_data(amount=amount)
    await state.set_state(WorkerExpenseStates.waiting_category)
    await message.answer("Select expense category:", reply_markup=_expense_category_kb())


@router.callback_query(F.data.startswith("exp_cat:"))
async def expense_category(callback: CallbackQuery, session: AsyncSession, worker, state: FSMContext, **kwargs):
    if not worker:
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    cat = callback.data.split(":")[1]
    if cat not in EXPENSE_CATEGORIES:
        await callback.answer("Invalid category", show_alert=True)
        return
    await state.update_data(category=cat)
    await state.set_state(WorkerExpenseStates.waiting_description)
    await callback.message.edit_text(
        f"Category: <b>{EXPENSE_CATEGORIES[cat]}</b>\n\n"
        "Enter a description of the expense:",
        reply_markup=_expense_cancel_kb()
    )
    await callback.answer()


@router.message(WorkerExpenseStates.waiting_description, F.text)
async def expense_description(message: Message, session: AsyncSession, worker, state: FSMContext, **kwargs):
    if not worker:
        return
    description = (message.text or "").strip()
    if not description or len(description) < 5:
        await message.answer(
            "❌ Description is required (min 5 characters).\n"
            "Explain what the expense is for.",
            reply_markup=_expense_cancel_kb()
        )
        return
    await state.update_data(description=description)
    await state.set_state(WorkerExpenseStates.waiting_receipt)
    await message.answer(
        "📎 <b>Attach receipt</b>\n\n"
        "Send a photo or PDF file of the receipt/invoice.\n"
        "This is <b>required</b> for approval.",
        reply_markup=_expense_cancel_kb()
    )


@router.message(WorkerExpenseStates.waiting_receipt, F.photo)
async def expense_receipt_photo(message: Message, session: AsyncSession, worker, state: FSMContext, **kwargs):
    if not worker:
        return
    file_id = message.photo[-1].file_id
    await _save_expense_report(message, session, worker, state, file_id)


@router.message(WorkerExpenseStates.waiting_receipt, F.document)
async def expense_receipt_document(message: Message, session: AsyncSession, worker, state: FSMContext, **kwargs):
    if not worker:
        return
    doc = message.document
    if doc.mime_type not in ("application/pdf", "image/jpeg", "image/png", "image/webp"):
        await message.answer(
            "❌ Only photo or PDF files accepted.\n"
            "Please send a valid receipt.",
            reply_markup=_expense_cancel_kb()
        )
        return
    await _save_expense_report(message, session, worker, state, doc.file_id)


@router.message(WorkerExpenseStates.waiting_receipt)
async def expense_receipt_invalid(message: Message, **kwargs):
    await message.answer(
        "❌ Please send a <b>photo</b> or <b>PDF file</b> as receipt.",
        reply_markup=_expense_cancel_kb()
    )


async def _save_expense_report(message: Message, session: AsyncSession, worker, state: FSMContext, receipt_file_id: str):
    data = await state.get_data()
    amount = data.get("amount", 0)
    category = data.get("category", "other")
    description = data.get("description")

    r = WorkerExpenseReport(
        worker_id=worker.id,
        amount=Decimal(str(amount)),
        category=category,
        description=description,
        receipt_file_id=receipt_file_id,
        status="pending",
    )
    session.add(r)
    await session.commit()
    await state.clear()

    cat_label = EXPENSE_CATEGORIES.get(category, category)
    await message.answer(
        f"✅ <b>Expense report submitted!</b>\n\n"
        f"Amount: <b>${amount:.2f}</b>\n"
        f"Category: {cat_label}\n"
        f"Description: {description}\n"
        f"Receipt: ✅ Attached\n\n"
        f"Status: <b>Pending admin approval</b>",
        reply_markup=profile_keyboard(worker)
    )
