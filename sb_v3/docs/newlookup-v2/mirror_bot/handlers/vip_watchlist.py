"""VIP Watchlist handler — $500 purchase with balance check, confirmation, auto-buy."""
from __future__ import annotations

import logging
from decimal import Decimal

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import SystemSetting
from mirror_bot.services.user_service import UserService
from mirror_bot.services.order_service import OrderService
from mirror_bot.utils.message_utils import safe_edit_message

logger = logging.getLogger(__name__)
router = Router()

VIP_PRICE = Decimal("500.00")


async def _load_vip_settings(session: AsyncSession) -> tuple[str, str | None]:
    """Returns (description, video_file_id|None)."""
    desc_row = await session.scalar(
        select(SystemSetting).where(SystemSetting.key == "vip_watchlist_description")
    )
    video_row = await session.scalar(
        select(SystemSetting).where(SystemSetting.key == "vip_watchlist_video_file_id")
    )
    description = (desc_row.value if desc_row else None) or (
        "🌟 *VIP Watchlist — $500*\n\n"
        "Priority access to the best accounts.\n"
        "Your order is personally fulfilled by our top specialists.\n\n"
        "✅ Instant order creation\n"
        "🔒 Guaranteed fulfillment within 24h\n"
        "👑 VIP-only exclusives"
    )
    video_file_id = video_row.value if video_row and video_row.value else None
    return description, video_file_id


def _vip_main_keyboard(user_balance: Decimal) -> InlineKeyboardMarkup:
    has_funds = user_balance >= VIP_PRICE
    rows = []
    if has_funds:
        rows.append([InlineKeyboardButton(
            text=f"💎 Purchase VIP — ${VIP_PRICE:.0f}",
            callback_data="vip_buy_confirm",
        )])
    else:
        shortage = VIP_PRICE - user_balance
        rows.append([InlineKeyboardButton(
            text=f"🔴 Insufficient balance (need ${shortage:.2f} more)",
            callback_data="vip_noop",
        )])
        rows.append([InlineKeyboardButton(
            text="💳 Top Up Balance",
            callback_data="vip_topup",
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def vip_watchlist_main_handler(
    message: Message,
    session: AsyncSession,
    mirror_bot_id: int,
    texts,
    buttons,
) -> None:
    description, video_file_id = await _load_vip_settings(session)
    user = await UserService.get_user(session, message.from_user.id, mirror_bot_id)
    balance = user.balance if user else Decimal("0")

    caption = (
        description + f"\n\n💳 *Your balance:* ${balance:.2f}"
    )
    kb = _vip_main_keyboard(balance)

    if video_file_id:
        try:
            await message.answer_video(video=video_file_id, caption=caption, reply_markup=kb, parse_mode="Markdown")
            return
        except Exception:
            pass
    await message.answer(caption, reply_markup=kb, parse_mode="Markdown")


# ── Callbacks ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "vip_watchlist_open")
async def vip_open_callback(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    description, video_file_id = await _load_vip_settings(session)
    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    balance = user.balance if user else Decimal("0")
    caption = description + f"\n\n💳 *Your balance:* ${balance:.2f}"
    kb = _vip_main_keyboard(balance)
    try:
        await callback.message.delete()
    except Exception:
        pass
    if video_file_id:
        try:
            await callback.bot.send_video(
                chat_id=callback.message.chat.id,
                video=video_file_id,
                caption=caption,
                reply_markup=kb,
                parse_mode="Markdown",
            )
            await callback.answer()
            return
        except Exception:
            pass
    await callback.bot.send_message(
        chat_id=callback.message.chat.id,
        text=caption,
        reply_markup=kb,
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "vip_noop")
async def vip_noop(callback: CallbackQuery):
    await callback.answer("Top up your balance to purchase VIP Watchlist.", show_alert=True)


@router.callback_query(F.data == "vip_topup")
async def vip_topup_callback(callback: CallbackQuery, texts, buttons):
    """Redirect to the top-up flow."""
    from mirror_bot.keyboards.inline import topup_keyboard
    await safe_edit_message(
        callback,
        "💳 *Top Up Balance*\n\nChoose a payment method:",
        reply_markup=topup_keyboard(buttons),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "vip_buy_confirm")
async def vip_buy_confirm(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int):
    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    balance = user.balance if user else Decimal("0")

    if balance < VIP_PRICE:
        shortage = VIP_PRICE - balance
        await callback.answer(
            f"❌ Insufficient balance. You need ${shortage:.2f} more.",
            show_alert=True,
        )
        return

    await safe_edit_message(
        callback,
        f"⚠️ *Confirm VIP Watchlist Purchase*\n\n"
        f"💎 *Price:* ${VIP_PRICE:.0f}\n"
        f"💳 *Your balance:* ${balance:.2f}\n"
        f"💰 *Balance after:* ${balance - VIP_PRICE:.2f}\n\n"
        f"Your order will be created instantly and fulfilled by our VIP team.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Confirm Purchase", callback_data="vip_buy_execute")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="vip_watchlist_open")],
        ]),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "vip_buy_execute")
async def vip_buy_execute(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int):
    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    if not user or user.balance < VIP_PRICE:
        await callback.answer("❌ Insufficient balance.", show_alert=True)
        return

    success = await OrderService.deduct_balance(session, callback.from_user.id, VIP_PRICE)
    if not success:
        await callback.answer("❌ Payment failed. Please try again.", show_alert=True)
        return

    order = await OrderService.create_order(
        session,
        user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
        category="vip_watchlist",
        service_name="VIP Watchlist",
        input_data={"type": "vip_watchlist", "price": str(VIP_PRICE)},
        price=VIP_PRICE,
        original_price=VIP_PRICE,
    )

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    await safe_edit_message(
        callback,
        f"✅ *VIP Watchlist — Order #{order.id} Created!*\n\n"
        f"💎 *Paid:* ${VIP_PRICE:.0f}\n"
        f"💳 *Remaining balance:* ${user.balance:.2f}\n\n"
        f"👑 Your VIP order is now in the queue.\n"
        f"Our specialists will contact you within 24 hours.\n\n"
        f"📬 Updates will be sent here.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📞 Contact Support", callback_data="support_category_general")],
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")],
        ]),
        parse_mode="Markdown",
    )
    await callback.answer("✅ Order created successfully!", show_alert=False)
