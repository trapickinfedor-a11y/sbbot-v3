from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from mirror_bot.keyboards.inline import bulk_confirmation_keyboard, confirm_keyboard
from mirror_bot.services.checkout_coupon_service import CheckoutCouponService
from mirror_bot.utils.message_utils import safe_edit_message

router = Router(name="checkout_coupons")


def _confirmation_keyboard(buttons, state_data: dict) -> InlineKeyboardMarkup:
    keyboard_type = state_data.get("checkout_keyboard_type", "confirm")
    suffix = state_data.get("checkout_keyboard_suffix", "")
    if keyboard_type == "custom":
        confirm_callback = state_data.get("checkout_confirm_callback")
        cancel_callback = state_data.get("checkout_cancel_callback")
        rows = []
        if confirm_callback:
            rows.append([InlineKeyboardButton(text="✅ Confirm", callback_data=confirm_callback)])
        if cancel_callback:
            rows.append([InlineKeyboardButton(text="❌ Cancel", callback_data=cancel_callback)])
        return InlineKeyboardMarkup(inline_keyboard=rows)
    if keyboard_type == "bulk":
        return bulk_confirmation_keyboard(buttons, suffix=suffix)
    return confirm_keyboard(buttons, suffix=suffix)


def _coupon_selection_keyboard(coupons, selected_user_coupon_id: int | None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for user_coupon in coupons:
        coupon = user_coupon.coupon
        if not coupon:
            continue
        label = coupon.code
        if coupon.discount_type == "percent":
            label += f" ({float(coupon.discount_value):.0f}%)"
        else:
            label += f" (${float(coupon.discount_value):.2f})"
        if selected_user_coupon_id == user_coupon.id:
            label = f"✅ {label}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"checkout_coupon_apply:{user_coupon.id}")])
    rows.append([InlineKeyboardButton(text="🗑 Clear Coupon", callback_data="checkout_coupon_clear")])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="checkout_coupon_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "checkout_coupon_menu")
async def checkout_coupon_menu(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    mirror_bot_id: int,
    buttons,
):
    state_data = await state.get_data()
    if "checkout_category" not in state_data:
        await callback.answer()
        return
    coupons = await CheckoutCouponService.get_available_user_coupons(
        session,
        telegram_user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
    )
    if not coupons:
        await callback.answer("No activated coupons available", show_alert=True)
        return
    text = (state_data.get("checkout_confirm_text") or "") + "\n\n🎟 Select one activated coupon for this purchase:"
    await safe_edit_message(
        callback,
        text,
        reply_markup=_coupon_selection_keyboard(coupons, state_data.get("selected_user_coupon_id")),
        parse_mode=state_data.get("checkout_parse_mode"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("checkout_coupon_apply:"))
async def checkout_coupon_apply(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    mirror_bot_id: int,
    buttons,
):
    state_data = await state.get_data()
    if "checkout_category" not in state_data:
        await callback.answer()
        return
    user_coupon_id = int(callback.data.split(":", 1)[1])
    user_coupon = await CheckoutCouponService.get_selected_coupon(
        session,
        telegram_user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
        user_coupon_id=user_coupon_id,
    )
    if not user_coupon or not user_coupon.coupon:
        await callback.answer("Coupon not found", show_alert=True)
        return
    await state.update_data(
        selected_coupon_code=user_coupon.coupon.code,
        selected_user_coupon_id=user_coupon.id,
    )
    updated_state = await state.get_data()
    text = await CheckoutCouponService.render_confirmation_text(
        session,
        telegram_user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
        state_data=updated_state,
    )
    await safe_edit_message(
        callback,
        text,
        reply_markup=_confirmation_keyboard(buttons, updated_state),
        parse_mode=updated_state.get("checkout_parse_mode"),
    )
    await callback.answer("Coupon selected")


@router.callback_query(F.data == "checkout_coupon_clear")
async def checkout_coupon_clear(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, buttons):
    state_data = await state.get_data()
    if "checkout_category" not in state_data:
        await callback.answer()
        return
    await state.update_data(selected_coupon_code=None, selected_user_coupon_id=None)
    updated_state = await state.get_data()
    text = await CheckoutCouponService.render_confirmation_text(
        session,
        telegram_user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
        state_data=updated_state,
    )
    await safe_edit_message(
        callback,
        text,
        reply_markup=_confirmation_keyboard(buttons, updated_state),
        parse_mode=updated_state.get("checkout_parse_mode"),
    )
    await callback.answer("Coupon cleared")


@router.callback_query(F.data == "checkout_coupon_back")
async def checkout_coupon_back(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, buttons):
    state_data = await state.get_data()
    if "checkout_category" not in state_data:
        await callback.answer()
        return
    text = await CheckoutCouponService.render_confirmation_text(
        session,
        telegram_user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
        state_data=state_data,
    )
    await safe_edit_message(
        callback,
        text,
        reply_markup=_confirmation_keyboard(buttons, state_data),
        parse_mode=state_data.get("checkout_parse_mode"),
    )
    await callback.answer()
