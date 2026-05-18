from __future__ import annotations

"""Marketer bot — withdrawal with wallet selection (BTC / USDT)"""
import logging
from decimal import Decimal, InvalidOperation
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import Marketer, MarketerWithdrawal
from marketer_bot.constants.language_loader import get_texts

logger = logging.getLogger(__name__)
router = Router(name="marketer_withdrawal")

MIN_WITHDRAW = Decimal("100.00")


class WithdrawFSM(StatesGroup):
    waiting_amount = State()
    waiting_wallet = State()
    waiting_address = State()
    waiting_confirm = State()


async def _get_marketer(session: AsyncSession, telegram_id: int):
    r = await session.execute(select(Marketer).where(Marketer.telegram_id == telegram_id))
    return r.scalar_one_or_none()


def _cancel_kb(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t.BTN_CANCEL, callback_data="marketer_dashboard")]
    ])


def _withdraw_menu_kb(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t.BTN_WITHDRAW, callback_data="mw_start")],
        [InlineKeyboardButton(text=t.BTN_WITHDRAW_HISTORY, callback_data="mw_history")],
        [InlineKeyboardButton(text=t.BTN_BACK, callback_data="marketer_dashboard")],
    ])


# ── Menu ──

@router.callback_query(F.data == "marketer_withdraw")
async def cb_withdraw_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext, texts=None, **kwargs):
    await state.clear()
    marketer = await _get_marketer(session, callback.from_user.id)
    if not marketer:
        await callback.answer("Not found", show_alert=True)
        return
    t = texts or get_texts(marketer.language)
    balance = float(marketer.balance or 0)
    text = (
        f"{t.WITHDRAW_TITLE}\n\n"
        f"{t.WITHDRAW_BALANCE.format(balance=f'{balance:.2f}')}\n"
        f"{t.WITHDRAW_MIN.format(min=f'{float(MIN_WITHDRAW):.2f}')}"
    )
    await callback.message.edit_text(text, reply_markup=_withdraw_menu_kb(t))
    await callback.answer()


# ── Start → enter amount ──

@router.callback_query(F.data == "mw_start")
async def cb_withdraw_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext, texts=None, **kwargs):
    marketer = await _get_marketer(session, callback.from_user.id)
    if not marketer:
        await callback.answer("Not found", show_alert=True)
        return
    t = texts or get_texts(marketer.language)
    balance = marketer.balance or Decimal("0")

    if balance < MIN_WITHDRAW:
        await callback.answer(t.WITHDRAW_NO_FUNDS, show_alert=True)
        return

    await state.set_state(WithdrawFSM.waiting_amount)
    await state.update_data(balance=str(balance))
    text = (
        f"{t.WITHDRAW_TITLE}\n\n"
        f"{t.WITHDRAW_BALANCE.format(balance=f'{float(balance):.2f}')}\n\n"
        f"{t.WITHDRAW_ENTER_AMOUNT}"
    )
    await callback.message.edit_text(text, reply_markup=_cancel_kb(t))
    await callback.answer()


# ── Amount → choose wallet ──

@router.message(WithdrawFSM.waiting_amount)
async def fsm_withdraw_amount(message: Message, session: AsyncSession, state: FSMContext, texts=None, **kwargs):
    marketer = await _get_marketer(session, message.from_user.id)
    t = texts or get_texts(marketer.language if marketer else None)

    try:
        amount = Decimal((message.text or "").strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        amount = Decimal("-1")

    balance = Decimal((await state.get_data()).get("balance", "0"))

    if amount < MIN_WITHDRAW or amount > balance:
        await message.answer(
            t.WITHDRAW_BAD_AMOUNT.format(min=f"{float(MIN_WITHDRAW):.2f}", max=f"{float(balance):.2f}"),
            reply_markup=_cancel_kb(t),
        )
        return

    await state.update_data(amount=str(amount))
    await state.set_state(WithdrawFSM.waiting_wallet)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t.BTN_WALLET_BTC, callback_data="mw_wallet_btc"),
            InlineKeyboardButton(text=t.BTN_WALLET_USDT, callback_data="mw_wallet_usdt"),
        ],
        [InlineKeyboardButton(text=t.BTN_CANCEL, callback_data="marketer_dashboard")],
    ])
    await message.answer(t.WITHDRAW_CHOOSE_WALLET, reply_markup=kb)


# ── Wallet chosen → enter address ──

@router.callback_query(F.data.in_({"mw_wallet_btc", "mw_wallet_usdt"}), WithdrawFSM.waiting_wallet)
async def cb_withdraw_wallet(callback: CallbackQuery, session: AsyncSession, state: FSMContext, texts=None, **kwargs):
    marketer = await _get_marketer(session, callback.from_user.id)
    t = texts or get_texts(marketer.language if marketer else None)

    wallet_type = "btc" if callback.data == "mw_wallet_btc" else "usdt"
    await state.update_data(wallet_type=wallet_type)
    await state.set_state(WithdrawFSM.waiting_address)

    prompt = t.WITHDRAW_ENTER_ADDRESS_BTC if wallet_type == "btc" else t.WITHDRAW_ENTER_ADDRESS_USDT
    await callback.message.edit_text(prompt, reply_markup=_cancel_kb(t))
    await callback.answer()


# ── Ignore text in waiting_wallet state ──

@router.message(WithdrawFSM.waiting_wallet)
async def fsm_withdraw_wallet_ignore(message: Message, session: AsyncSession, state: FSMContext, texts=None, **kwargs):
    marketer = await _get_marketer(session, message.from_user.id)
    t = texts or get_texts(marketer.language if marketer else None)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t.BTN_WALLET_BTC, callback_data="mw_wallet_btc"),
            InlineKeyboardButton(text=t.BTN_WALLET_USDT, callback_data="mw_wallet_usdt"),
        ],
        [InlineKeyboardButton(text=t.BTN_CANCEL, callback_data="marketer_dashboard")],
    ])
    await message.answer(t.WITHDRAW_CHOOSE_WALLET, reply_markup=kb)


# ── Address → confirm ──

@router.message(WithdrawFSM.waiting_address)
async def fsm_withdraw_address(message: Message, session: AsyncSession, state: FSMContext, texts=None, **kwargs):
    marketer = await _get_marketer(session, message.from_user.id)
    t = texts or get_texts(marketer.language if marketer else None)

    address = (message.text or "").strip()
    if not address or len(address) < 10:
        data = await state.get_data()
        wallet_type = data.get("wallet_type", "usdt")
        prompt = t.WITHDRAW_ENTER_ADDRESS_BTC if wallet_type == "btc" else t.WITHDRAW_ENTER_ADDRESS_USDT
        await message.answer(prompt, reply_markup=_cancel_kb(t))
        return

    data = await state.get_data()
    wallet_type = data.get("wallet_type", "usdt")
    amount = data["amount"]

    if wallet_type == "btc":
        requisites = f"BTC: {address}"
    else:
        requisites = f"USDT TRC-20: {address}"

    await state.update_data(requisites=requisites)
    await state.set_state(WithdrawFSM.waiting_confirm)

    text = t.WITHDRAW_CONFIRM.format(amount=amount, requisites=requisites)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t.BTN_CONFIRM_WITHDRAW, callback_data="mw_confirm")],
        [InlineKeyboardButton(text=t.BTN_CANCEL, callback_data="marketer_dashboard")],
    ])
    await message.answer(text, reply_markup=kb)


# ── Confirm → create withdrawal ──

@router.callback_query(F.data == "mw_confirm", WithdrawFSM.waiting_confirm)
async def cb_withdraw_confirm(callback: CallbackQuery, session: AsyncSession, state: FSMContext, texts=None, **kwargs):
    marketer = await _get_marketer(session, callback.from_user.id)
    if not marketer:
        await state.clear()
        await callback.answer("Not found", show_alert=True)
        return
    t = texts or get_texts(marketer.language)

    data = await state.get_data()
    amount = Decimal(data["amount"])
    requisites = data["requisites"]

    if (marketer.balance or Decimal("0")) < amount:
        await state.clear()
        await callback.answer(t.WITHDRAW_NO_FUNDS, show_alert=True)
        return

    marketer.balance -= amount
    withdrawal = MarketerWithdrawal(
        marketer_id=marketer.id,
        amount=amount,
        requisites=requisites,
        status="pending",
        funds_reserved=True,
    )
    session.add(withdrawal)
    await session.commit()
    await state.clear()

    text = t.WITHDRAW_CREATED.format(amount=f"{float(amount):.2f}")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t.BTN_BACK, callback_data="marketer_dashboard")],
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ── History ──

@router.callback_query(F.data == "mw_history")
async def cb_withdraw_history(callback: CallbackQuery, session: AsyncSession, texts=None, **kwargs):
    marketer = await _get_marketer(session, callback.from_user.id)
    if not marketer:
        await callback.answer("Not found", show_alert=True)
        return
    t = texts or get_texts(marketer.language)

    result = await session.execute(
        select(MarketerWithdrawal)
        .where(MarketerWithdrawal.marketer_id == marketer.id)
        .order_by(MarketerWithdrawal.created_at.desc())
        .limit(15)
    )
    withdrawals = list(result.scalars().all())

    if not withdrawals:
        text = f"{t.WITHDRAW_HISTORY_TITLE}\n\n{t.WITHDRAW_HISTORY_EMPTY}"
    else:
        status_map = {
            "pending": t.WITHDRAW_STATUS_PENDING,
            "approved": t.WITHDRAW_STATUS_APPROVED,
            "rejected": t.WITHDRAW_STATUS_REJECTED,
        }
        lines = []
        for w in withdrawals:
            dt = w.created_at.strftime("%d.%m.%Y") if w.created_at else "—"
            st = status_map.get(w.status, w.status)
            rej = f"\n   ↳ {w.reject_reason}" if w.status == "rejected" and w.reject_reason else ""
            lines.append(f"• {dt}  <b>${float(w.amount):.2f}</b>  {st}{rej}")
        text = f"{t.WITHDRAW_HISTORY_TITLE}\n\n" + "\n".join(lines)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t.BTN_BACK, callback_data="marketer_withdraw")],
    ])
    await callback.message.edit_text(text[:4000], reply_markup=kb)
    await callback.answer()
