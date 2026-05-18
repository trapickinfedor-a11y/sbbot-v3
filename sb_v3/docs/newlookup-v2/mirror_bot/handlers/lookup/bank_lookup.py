"""
Lookup BA — проверка банковских аккаунтов по номеру аккаунта, роутингу, имени и т.д.
5 типов проверок, цены из ServicePrice БД.
"""

import logging
from decimal import Decimal

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from mirror_bot.services.order_service import OrderService
from mirror_bot.services.checkout_coupon_service import CheckoutCouponService
from mirror_bot.services.user_service import UserService
from mirror_bot.constants.service_eta import ServiceETA
from mirror_bot.utils.message_utils import safe_edit_message

logger = logging.getLogger(__name__)
router = Router()

# ─── Цены (fallback, если ServicePrice не заполнен) ──────────────────────────
BA_SERVICES = {
    "lookup_ba_an_rn": {
        "name": "Check AN+RN",
        "description": "Check Account Number + Routing Number",
        "price": Decimal("5.00"),
        "input_hint": "Enter Account Number and Routing Number:\n\nFormat: `AccountNumber / RoutingNumber`\nExample: `123456789 / 021000021`",
    },
    "lookup_ba_transactions": {
        "name": "Check Transactions [15 days]",
        "description": "View last 15 days of transactions",
        "price": Decimal("5.00"),
        "input_hint": "Enter Account Number and Routing Number:\n\nFormat: `AccountNumber / RoutingNumber`\nExample: `123456789 / 021000021`",
    },
    "lookup_ba_balance": {
        "name": "Check Balance",
        "description": "Check current account balance",
        "price": Decimal("5.00"),
        "input_hint": "Enter Account Number and Routing Number:\n\nFormat: `AccountNumber / RoutingNumber`\nExample: `123456789 / 021000021`",
    },
    "lookup_ba_name": {
        "name": "Check NAME",
        "description": "Get account holder name by AN+RN",
        "price": Decimal("3.00"),
        "input_hint": "Enter Account Number and Routing Number:\n\nFormat: `AccountNumber / RoutingNumber`\nExample: `123456789 / 021000021`",
    },
    "lookup_ba_an_rn_name": {
        "name": "Check AN+RN+NAME",
        "description": "Full check: account, routing and name",
        "price": Decimal("7.00"),
        "input_hint": "Enter Account Number and Routing Number:\n\nFormat: `AccountNumber / RoutingNumber`\nExample: `123456789 / 021000021`",
    },
}


class BankLookupStates(StatesGroup):
    waiting_input = State()
    confirming = State()


def _get_price(service_key: str) -> Decimal:
    """Получить цену из BA_SERVICES (можно расширить загрузкой из ServicePrice)."""
    return BA_SERVICES[service_key]["price"]


def _ba_catalog_keyboard(buttons) -> InlineKeyboardMarkup:
    rows = []
    for key, info in BA_SERVICES.items():
        rows.append([InlineKeyboardButton(
            text=f"🏦 {info['name']} — ${info['price']}",
            callback_data=f"lookup_ba_item:{key}"
        )])
    rows.append([InlineKeyboardButton(text=buttons.BACK, callback_data="back_lookup")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _ba_confirm_keyboard(buttons) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.CONFIRM_PAY, callback_data="ba_confirm_yes")],
        [InlineKeyboardButton(text=buttons.CANCEL, callback_data="ba_confirm_no")],
    ])


# ─── Handlers ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "lookup_ba")
async def lookup_ba_main(callback: CallbackQuery, state: FSMContext, texts, buttons):
    """Главное меню Bank Account Lookup."""
    await state.clear()
    await safe_edit_message(
        callback,
        "🏦 *Bank Account Lookup*\n\nSelect the type of check you need:",
        reply_markup=_ba_catalog_keyboard(buttons),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lookup_ba_item:"))
async def lookup_ba_item_selected(callback: CallbackQuery, state: FSMContext, session: AsyncSession, texts, buttons):
    """Пользователь выбрал тип проверки — запрашиваем данные."""
    service_key = callback.data.split(":", 1)[1]
    if service_key not in BA_SERVICES:
        await callback.answer("Unknown service", show_alert=True)
        return

    info = BA_SERVICES[service_key]
    price = _get_price(service_key)

    await state.update_data(service_key=service_key, price=str(price))
    await state.set_state(BankLookupStates.waiting_input)

    await safe_edit_message(
        callback,
        f"🏦 *{info['name']}* — ${price}\n\n{info['input_hint']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=buttons.CANCEL, callback_data="lookup_ba")]
        ]),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(BankLookupStates.waiting_input)
async def lookup_ba_input_received(message: Message, state: FSMContext, session: AsyncSession, texts, buttons, mirror_bot_id: int):
    """Получили данные от пользователя — показываем подтверждение."""
    data = await state.get_data()
    service_key = data.get("service_key")
    price = Decimal(data.get("price", "0"))

    if service_key not in BA_SERVICES:
        await state.clear()
        return

    info = BA_SERVICES[service_key]
    user_input = message.text.strip()

    user = await UserService.get_user(session, message.from_user.id, mirror_bot_id)

    await state.update_data(user_input=user_input)
    await state.set_state(BankLookupStates.confirming)

    confirm_text = (
        f"✅ *Confirm your order*\n\n"
        f"📋 *Service:* {info['name']}\n"
        f"📝 *Your data:*\n`{user_input}`\n\n"
        f"💰 *Price:* ${price:.2f}\n"
        f"💳 *Your balance:* ${user.balance:.2f}\n"
        f"💳 *After payment:* ${user.balance - price:.2f}\n\n"
        f"⏱ *ETA:* {ServiceETA.get_eta('lookup')}"
    )
    await state.update_data(
        checkout_category="lookup_ba",
        checkout_service_name=service_key,
        checkout_base_price=str(price),
        checkout_confirm_text=confirm_text,
        checkout_keyboard_type="custom",
        checkout_confirm_callback="ba_confirm_yes",
        checkout_cancel_callback="ba_confirm_no",
        checkout_parse_mode="Markdown",
        selected_coupon_code=None,
        selected_user_coupon_id=None,
    )
    await message.answer(confirm_text, reply_markup=_ba_confirm_keyboard(buttons), parse_mode="Markdown")


@router.callback_query(F.data == "ba_confirm_yes", BankLookupStates.confirming)
async def lookup_ba_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession, texts, buttons, mirror_bot_id: int):
    """Подтверждение заказа — создаём Order."""
    data = await state.get_data()
    service_key = data.get("service_key")
    price = Decimal(data.get("price", "0"))
    user_input = data.get("user_input", "")

    if service_key not in BA_SERVICES:
        await state.clear()
        await callback.answer("Error: service not found", show_alert=True)
        return

    info = BA_SERVICES[service_key]

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    pricing = await CheckoutCouponService.get_checkout_pricing(
        session,
        telegram_user_id=callback.from_user.id,
        state_data=data,
    )
    if not user or user.balance < pricing.final_amount:
        await callback.answer("Insufficient balance", show_alert=True)
        await state.clear()
        return

    try:
        success = await OrderService.deduct_balance(session, callback.from_user.id, pricing.final_amount)
        if not success:
            await callback.answer("Insufficient balance", show_alert=True)
            await state.clear()
            return
        order = await OrderService.create_order(
            session,
            user_id=callback.from_user.id,
            mirror_bot_id=mirror_bot_id,
            category="lookup_ba",
            service_name=service_key,
            input_data={"service": service_key, "data": user_input},
            price=pricing.final_amount,
            original_price=pricing.original_amount,
            coupon_code=pricing.code,
            discount_amount=pricing.discount_amount,
            coupon_application=pricing,
        )
        user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
        await state.clear()
        await safe_edit_message(
            callback,
            f"✅ *Order #{order.id} created!*\n\n"
            f"📋 *Service:* {info['name']}\n"
            f"💰 *Paid:* ${price:.2f}\n"
            f"💳 *Balance:* ${user.balance:.2f}\n\n"
            f"⏱ *ETA:* {ServiceETA.get_eta('lookup')}\n"
            f"📬 You'll receive the result here when ready.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")]
            ]),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Failed to create BA lookup order: {e}")
        await callback.answer("Error creating order. Please try again.", show_alert=True)
        await state.clear()

    await callback.answer()


@router.callback_query(F.data == "ba_confirm_no", BankLookupStates.confirming)
async def lookup_ba_cancel(callback: CallbackQuery, state: FSMContext, texts, buttons):
    """Отмена заказа."""
    await state.clear()
    await safe_edit_message(
        callback,
        "❌ Order cancelled.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏦 Back to Lookup BA", callback_data="lookup_ba")],
            [InlineKeyboardButton(text=buttons.BACK, callback_data="back_lookup")],
        ]),
    )
    await callback.answer()
