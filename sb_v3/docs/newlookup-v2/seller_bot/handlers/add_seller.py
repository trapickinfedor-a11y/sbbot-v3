"""seller_bot/handlers/add_seller.py

Allows an existing (approved) seller to invite a new seller by Telegram ID.

Flow:
1. Seller presses "Add Seller" button  → seller_add_seller_start (CallbackQuery)
2. Bot asks for Telegram ID            → FSM state: AddSellerStates.waiting_tg_id
3. Seller types the ID                 → seller_add_seller_tg_id (Message)
4. Bot validates and creates a draft   → notifies the invited user

Python 3.9-compatible (no walrus, no match/case, no X | Y union types).
"""
from __future__ import annotations

import logging
from typing import Optional

from aiogram import F, Router
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

from seller_bot.services.seller_service import SellerService
from shared.i18n import t

logger = logging.getLogger(__name__)
router = Router(name="seller_add_seller")


class AddSellerStates(StatesGroup):
    waiting_tg_id = State()


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------

def _back_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=t("common.cancel", lang),
            callback_data="seller_add_seller_cancel",
        )]
    ])


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "seller_add_seller")
async def seller_add_seller_start(
    callback: CallbackQuery,
    session: AsyncSession,
    is_seller: bool,
    seller,
    state: FSMContext,
    **kwargs,
) -> None:
    if not is_seller or not seller:
        await callback.answer(t("seller.no_access"), show_alert=True)
        return

    lang = getattr(seller, "language", None) or "en"
    await state.set_state(AddSellerStates.waiting_tg_id)
    await state.update_data(inviter_id=seller.id, inviter_tg_id=seller.telegram_id, lang=lang)

    await callback.message.edit_text(
        t("seller.add_seller_prompt", lang),
        reply_markup=_back_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(F.data == "seller_add_seller_cancel")
async def seller_add_seller_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    seller,
    **kwargs,
) -> None:
    await state.clear()
    lang = getattr(seller, "language", None) or "en" if seller else "en"
    await callback.message.edit_text(t("common.cancel", lang))
    await callback.answer()


@router.message(AddSellerStates.waiting_tg_id)
async def seller_add_seller_tg_id(
    message: Message,
    session: AsyncSession,
    seller,
    state: FSMContext,
    **kwargs,
) -> None:
    data = await state.get_data()
    lang = data.get("lang", "en")
    inviter_name = (
        getattr(seller, "display_name", None)
        or getattr(seller, "username", None)
        or str(getattr(seller, "telegram_id", "?"))
    ) if seller else "?"

    raw = (message.text or "").strip()
    try:
        target_tg_id = int(raw)
    except ValueError:
        await message.answer(
            t("seller.add_seller_invalid_id", lang),
            reply_markup=_back_keyboard(lang),
        )
        return

    # Check if already registered
    existing = await SellerService.get_seller(session, target_tg_id)
    if existing:
        status = getattr(existing, "access_status", "unknown") or "unknown"
        await message.answer(
            t("seller.add_seller_already_exists", lang, tg_id=target_tg_id, status=status),
            reply_markup=_back_keyboard(lang),
        )
        return

    # Create a draft seller record (pending_deposit, not yet rules_accepted)
    new_seller = await SellerService.register_seller(
        session,
        telegram_id=target_tg_id,
        username=None,
        display_name=str(target_tg_id),
        seller_type="external",
        language="en",
        rules_accepted=False,
    )

    display = new_seller.display_name or str(target_tg_id)
    await message.answer(
        t("seller.add_seller_success", lang, tg_id=target_tg_id, name=display)
    )

    # Notify the invited user
    try:
        await message.bot.send_message(
            chat_id=target_tg_id,
            text=t("seller.add_seller_invite_notification", "en", inviter_name=inviter_name),
            parse_mode="HTML",
        )
    except Exception as exc:
        logger.warning("Could not notify invited seller %s: %s", target_tg_id, exc)

    await state.clear()
