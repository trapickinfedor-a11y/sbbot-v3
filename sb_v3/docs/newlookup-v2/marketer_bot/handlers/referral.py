from __future__ import annotations

"""Marketer bot — referral program commands and FSM."""
import logging
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import Marketer
from shared.referral.service import ReferralService, generate_ref_code
from marketer_bot.config import marketer_bot_config
from marketer_bot.constants.language_loader import get_texts

logger = logging.getLogger(__name__)
router = Router(name="marketer_referral")

MIN_WITHDRAW_DEFAULT = Decimal("10.00")


# ── FSM ─────────────────────────────────────────────────────────────────────

class ReferralWithdrawFSM(StatesGroup):
    waiting_amount = State()
    waiting_requisites = State()
    waiting_confirm = State()


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_marketer(session: AsyncSession, telegram_id: int) -> Marketer | None:
    r = await session.execute(
        select(Marketer).where(Marketer.telegram_id == telegram_id)
    )
    return r.scalar_one_or_none()


def _build_referral_link(bot_username: str, telegram_id: int) -> str:
    """Build t.me/BOT?start=ref_USERID link."""
    ref_code = generate_ref_code(telegram_id)
    return f"https://t.me/{bot_username}?start={ref_code}"


def _referral_main_kb(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t.BTN_REFERRAL_STATS, callback_data="ref_stats")],
        [InlineKeyboardButton(text=t.BTN_REFERRAL_HISTORY, callback_data="ref_history:0")],
        [InlineKeyboardButton(text=t.BTN_REFERRAL_WITHDRAW, callback_data="ref_withdraw_menu")],
        [InlineKeyboardButton(text=t.BTN_BACK, callback_data="marketer_dashboard")],
    ])


def _back_kb(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t.BTN_BACK, callback_data="ref_main")],
    ])


def _cancel_kb(t) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t.BTN_CANCEL, callback_data="marketer_dashboard")],
    ])


def _status_label(status: str, t) -> str:
    mapping = {
        "pending_moderation": t.REFERRAL_STATUS_PENDING,
        "approved": t.REFERRAL_STATUS_APPROVED,
        "rejected": t.REFERRAL_STATUS_REJECTED,
        "paid": t.REFERRAL_STATUS_PAID,
    }
    return mapping.get(status, status)


# ── /referral command ────────────────────────────────────────────────────────

@router.message(Command("referral"))
async def cmd_referral(message: Message, session: AsyncSession, texts=None, **kwargs):
    marketer = await _get_marketer(session, message.from_user.id)
    if not marketer:
        await message.answer("Please /start first.")
        return
    t = texts or get_texts(marketer.language)
    await _show_referral_main(message, session, marketer, t, edit=False)


@router.callback_query(F.data == "ref_main")
async def cb_ref_main(callback: CallbackQuery, session: AsyncSession, texts=None, **kwargs):
    marketer = await _get_marketer(session, callback.from_user.id)
    if not marketer:
        await callback.answer("Not found", show_alert=True)
        return
    t = texts or get_texts(marketer.language)
    await _show_referral_main(callback.message, session, marketer, t, edit=True)
    await callback.answer()


async def _show_referral_main(
    message, session: AsyncSession, marketer: Marketer, t, *, edit: bool
):
    # Resolve bot username from the marketer bot token
    bot_username = await _resolve_bot_username(message)
    ref_link = _build_referral_link(bot_username, marketer.telegram_id)

    settings = await ReferralService.get_settings(session)

    text = (
        f"{t.REFERRAL_TITLE}\n\n"
        + t.REFERRAL_YOUR_LINK.format(
            link=ref_link,
            l1=settings.level1_display_pct,
            l2=settings.level2_display_pct,
            l3=settings.level3_display_pct,
            l4=settings.level4_display_pct,
        )
    )

    # Share button uses Telegram's share URL
    share_url = f"https://t.me/share/url?url={ref_link}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t.BTN_SHARE_LINK, url=share_url)],
        [InlineKeyboardButton(text=t.BTN_REFERRAL_STATS, callback_data="ref_stats")],
        [InlineKeyboardButton(text=t.BTN_REFERRAL_HISTORY, callback_data="ref_history:0")],
        [InlineKeyboardButton(text=t.BTN_REFERRAL_WITHDRAW, callback_data="ref_withdraw_menu")],
        [InlineKeyboardButton(text=t.BTN_BACK, callback_data="marketer_dashboard")],
    ])

    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


async def _resolve_bot_username(message) -> str:
    """Try to get bot username from the Bot object attached to message."""
    try:
        bot = message.bot
        if bot:
            me = await bot.get_me()
            return me.username or "bot"
    except Exception:
        pass
    return "bot"


# ── /referral_stats ──────────────────────────────────────────────────────────

@router.message(Command("referral_stats"))
async def cmd_referral_stats(message: Message, session: AsyncSession, texts=None, **kwargs):
    marketer = await _get_marketer(session, message.from_user.id)
    if not marketer:
        await message.answer("Please /start first.")
        return
    t = texts or get_texts(marketer.language)
    await _show_referral_stats(message, session, marketer, t, edit=False)


@router.callback_query(F.data == "ref_stats")
async def cb_ref_stats(callback: CallbackQuery, session: AsyncSession, texts=None, **kwargs):
    marketer = await _get_marketer(session, callback.from_user.id)
    if not marketer:
        await callback.answer("Not found", show_alert=True)
        return
    t = texts or get_texts(marketer.language)
    await _show_referral_stats(callback.message, session, marketer, t, edit=True)
    await callback.answer()


async def _show_referral_stats(message, session: AsyncSession, marketer: Marketer, t, *, edit: bool):
    stats = await ReferralService.get_referral_stats(session, marketer.telegram_id)
    text = (
        f"{t.REFERRAL_STATS_TITLE}\n\n"
        + t.REFERRAL_STATS_TEXT.format(
            invited=stats["total_invited"],
            confirmed=stats["confirmed"],
            earned=f"{stats['total_earned_display']:.2f}",
            pending=f"{stats['pending_moderation']:.2f}",
        )
    )
    kb = _back_kb(t)
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


# ── /referral_history ────────────────────────────────────────────────────────

PAGE_SIZE = 10


@router.message(Command("referral_history"))
async def cmd_referral_history(message: Message, session: AsyncSession, texts=None, **kwargs):
    marketer = await _get_marketer(session, message.from_user.id)
    if not marketer:
        await message.answer("Please /start first.")
        return
    t = texts or get_texts(marketer.language)
    await _show_referral_history(message, session, marketer, t, offset=0, edit=False)


@router.callback_query(F.data.startswith("ref_history:"))
async def cb_ref_history(callback: CallbackQuery, session: AsyncSession, texts=None, **kwargs):
    try:
        offset = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        offset = 0
    marketer = await _get_marketer(session, callback.from_user.id)
    if not marketer:
        await callback.answer("Not found", show_alert=True)
        return
    t = texts or get_texts(marketer.language)
    await _show_referral_history(callback.message, session, marketer, t, offset=offset, edit=True)
    await callback.answer()


async def _show_referral_history(
    message, session: AsyncSession, marketer: Marketer, t, *, offset: int, edit: bool
):
    rewards = await ReferralService.get_referral_history(
        session, marketer.telegram_id, limit=PAGE_SIZE + 1, offset=offset
    )
    has_more = len(rewards) > PAGE_SIZE
    rewards = rewards[:PAGE_SIZE]

    if not rewards and offset == 0:
        text = f"{t.REFERRAL_HISTORY_TITLE}\n\n{t.REFERRAL_HISTORY_EMPTY}"
    else:
        lines = [t.REFERRAL_HISTORY_TITLE, ""]
        for r in rewards:
            date_str = r.created_at.strftime("%d.%m.%Y") if r.created_at else "—"
            status_label = _status_label(r.status, t)
            lines.append(
                t.REFERRAL_HISTORY_ROW.format(
                    date=date_str,
                    level=r.level,
                    amount=f"{float(r.amount_display):.2f}",
                    status=status_label,
                )
            )
        text = "\n".join(lines)

    nav_buttons = []
    if offset > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="◀️", callback_data=f"ref_history:{offset - PAGE_SIZE}")
        )
    if has_more:
        nav_buttons.append(
            InlineKeyboardButton(text="▶️", callback_data=f"ref_history:{offset + PAGE_SIZE}")
        )

    rows = []
    if nav_buttons:
        rows.append(nav_buttons)
    rows.append([InlineKeyboardButton(text=t.BTN_BACK, callback_data="ref_main")])

    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    if edit:
        await message.edit_text(text[:4000], reply_markup=kb)
    else:
        await message.answer(text[:4000], reply_markup=kb)


# ── /referral_withdraw ───────────────────────────────────────────────────────

@router.message(Command("referral_withdraw"))
async def cmd_referral_withdraw(
    message: Message, session: AsyncSession, state: FSMContext, texts=None, **kwargs
):
    marketer = await _get_marketer(session, message.from_user.id)
    if not marketer:
        await message.answer("Please /start first.")
        return
    t = texts or get_texts(marketer.language)
    await _show_withdraw_menu(message, session, marketer, t, edit=False)


@router.callback_query(F.data == "ref_withdraw_menu")
async def cb_ref_withdraw_menu(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext, texts=None, **kwargs
):
    await state.clear()
    marketer = await _get_marketer(session, callback.from_user.id)
    if not marketer:
        await callback.answer("Not found", show_alert=True)
        return
    t = texts or get_texts(marketer.language)
    await _show_withdraw_menu(callback.message, session, marketer, t, edit=True)
    await callback.answer()


async def _show_withdraw_menu(message, session: AsyncSession, marketer: Marketer, t, *, edit: bool):
    balance = await ReferralService.get_available_balance(session, marketer.telegram_id)
    settings = await ReferralService.get_settings(session)
    min_w = Decimal(str(settings.min_withdrawal_usd))

    text = (
        f"{t.REFERRAL_WITHDRAW_TITLE}\n\n"
        f"{t.REFERRAL_WITHDRAW_BALANCE.format(balance=f'{float(balance):.2f}')}\n"
        f"{t.REFERRAL_WITHDRAW_MIN.format(min=f'{float(min_w):.2f}')}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t.BTN_REFERRAL_WITHDRAW, callback_data="ref_withdraw_start")],
        [InlineKeyboardButton(text=t.BTN_REFERRAL_HISTORY, callback_data="ref_withdraw_history")],
        [InlineKeyboardButton(text=t.BTN_BACK, callback_data="ref_main")],
    ])
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "ref_withdraw_start")
async def cb_ref_withdraw_start(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext, texts=None, **kwargs
):
    marketer = await _get_marketer(session, callback.from_user.id)
    if not marketer:
        await callback.answer("Not found", show_alert=True)
        return
    t = texts or get_texts(marketer.language)

    balance = await ReferralService.get_available_balance(session, marketer.telegram_id)
    settings = await ReferralService.get_settings(session)
    min_w = Decimal(str(settings.min_withdrawal_usd))

    if balance < min_w:
        await callback.answer(t.REFERRAL_WITHDRAW_NO_FUNDS, show_alert=True)
        return

    await state.set_state(ReferralWithdrawFSM.waiting_amount)
    await state.update_data(balance=str(balance), min_withdraw=str(min_w))

    text = (
        f"{t.REFERRAL_WITHDRAW_TITLE}\n\n"
        f"{t.REFERRAL_WITHDRAW_BALANCE.format(balance=f'{float(balance):.2f}')}\n\n"
        f"{t.REFERRAL_WITHDRAW_ENTER_AMOUNT}"
    )
    await callback.message.edit_text(text, reply_markup=_cancel_kb(t))
    await callback.answer()


@router.message(ReferralWithdrawFSM.waiting_amount)
async def fsm_ref_withdraw_amount(
    message: Message, session: AsyncSession, state: FSMContext, texts=None, **kwargs
):
    marketer = await _get_marketer(session, message.from_user.id)
    t = texts or get_texts(marketer.language if marketer else None)

    data = await state.get_data()
    balance = Decimal(data.get("balance", "0"))
    min_w = Decimal(data.get("min_withdraw", "10"))

    try:
        amount = Decimal((message.text or "").strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        amount = Decimal("-1")

    if amount < min_w or amount > balance:
        await message.answer(
            t.REFERRAL_WITHDRAW_BAD_AMOUNT.format(
                min=f"{float(min_w):.2f}", max=f"{float(balance):.2f}"
            ),
            reply_markup=_cancel_kb(t),
        )
        return

    await state.update_data(amount=str(amount))
    await state.set_state(ReferralWithdrawFSM.waiting_requisites)
    await message.answer(t.REFERRAL_WITHDRAW_ENTER_REQUISITES, reply_markup=_cancel_kb(t))


@router.message(ReferralWithdrawFSM.waiting_requisites)
async def fsm_ref_withdraw_requisites(
    message: Message, session: AsyncSession, state: FSMContext, texts=None, **kwargs
):
    marketer = await _get_marketer(session, message.from_user.id)
    t = texts or get_texts(marketer.language if marketer else None)

    requisites = (message.text or "").strip()
    if not requisites or len(requisites) < 5:
        await message.answer(t.REFERRAL_WITHDRAW_ENTER_REQUISITES, reply_markup=_cancel_kb(t))
        return

    data = await state.get_data()
    amount = data["amount"]
    await state.update_data(requisites=requisites)
    await state.set_state(ReferralWithdrawFSM.waiting_confirm)

    text = t.REFERRAL_WITHDRAW_CONFIRM.format(amount=amount, requisites=requisites)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t.BTN_CONFIRM_REFERRAL_WITHDRAW, callback_data="ref_withdraw_confirm")],
        [InlineKeyboardButton(text=t.BTN_CANCEL, callback_data="marketer_dashboard")],
    ])
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "ref_withdraw_confirm", ReferralWithdrawFSM.waiting_confirm)
async def cb_ref_withdraw_confirm(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext, texts=None, **kwargs
):
    marketer = await _get_marketer(session, callback.from_user.id)
    if not marketer:
        await state.clear()
        await callback.answer("Not found", show_alert=True)
        return
    t = texts or get_texts(marketer.language)

    data = await state.get_data()
    amount = float(data["amount"])
    requisites = data["requisites"]

    withdrawal = await ReferralService.request_referral_withdrawal(
        session, marketer.telegram_id, amount, requisites
    )
    await session.commit()
    await state.clear()

    if withdrawal is None:
        await callback.answer(t.REFERRAL_WITHDRAW_NO_FUNDS, show_alert=True)
        return

    text = t.REFERRAL_WITHDRAW_CREATED.format(amount=f"{amount:.2f}")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t.BTN_BACK, callback_data="ref_main")],
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# ── Withdrawal history ────────────────────────────────────────────────────────

@router.callback_query(F.data == "ref_withdraw_history")
async def cb_ref_withdraw_history(
    callback: CallbackQuery, session: AsyncSession, texts=None, **kwargs
):
    marketer = await _get_marketer(session, callback.from_user.id)
    if not marketer:
        await callback.answer("Not found", show_alert=True)
        return
    t = texts or get_texts(marketer.language)

    withdrawals = await ReferralService.get_withdrawal_history(session, marketer.telegram_id)

    if not withdrawals:
        text = f"{t.REFERRAL_HISTORY_TITLE}\n\n{t.REFERRAL_HISTORY_EMPTY}"
    else:
        status_map = {
            "pending_moderation": t.REFERRAL_STATUS_PENDING,
            "approved": t.REFERRAL_STATUS_APPROVED,
            "rejected": t.REFERRAL_STATUS_REJECTED,
        }
        lines = [t.REFERRAL_WITHDRAW_TITLE, ""]
        for w in withdrawals:
            date_str = w.created_at.strftime("%d.%m.%Y") if w.created_at else "—"
            st = status_map.get(w.status, w.status)
            rej = f"\n   ↳ {w.reject_reason}" if w.status == "rejected" and w.reject_reason else ""
            lines.append(f"• {date_str}  <b>${float(w.amount):.2f}</b>  {st}{rej}")
        text = "\n".join(lines)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t.BTN_BACK, callback_data="ref_withdraw_menu")],
    ])
    await callback.message.edit_text(text[:4000], reply_markup=kb)
    await callback.answer()
