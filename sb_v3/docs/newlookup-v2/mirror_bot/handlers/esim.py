from __future__ import annotations

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from decimal import Decimal
from mirror_bot.keyboards.inline import esim_main_keyboard
from mirror_bot.services.order_service import OrderService
from mirror_bot.services.checkout_coupon_service import CheckoutCouponService
from mirror_bot.services.user_service import UserService
from mirror_bot.constants.prices import ServicePrices, BulkDiscounts
from mirror_bot.constants.service_eta import ServiceETA
from mirror_bot.states.order import ESIMStates, ESIMConfigStates
from mirror_bot.utils.message_utils import safe_edit_message
from mirror_bot.utils.media_library import resolve_bot_photo
from shared.database.models import AccountItem, AccountInventory

logger = logging.getLogger(__name__)

router = Router()

ESIM_PHOTO = resolve_bot_photo("esim", fallback_path="media/esim.png")

_ESIM_SMS_CAT = "esim_sms"
_ESIM_DATA_CAT = "esim_data"
_GV_CAT = "gv"
# Только эти AccountItem допустимы в eSIM-флоу (защита от подстановки id из других каталогов)
_ESIM_CATALOG_CATEGORIES = frozenset({_ESIM_SMS_CAT, _ESIM_DATA_CAT, _GV_CAT})

OPERATOR_PRICES = {
    "verizon": {
        "1": ServicePrices.ESIM_VERIZON,
        "3": ServicePrices.ESIM_VERIZON_3,
        "6": ServicePrices.ESIM_VERIZON_6,
    },
    "att": {
        "1": ServicePrices.ESIM_ATT,
        "3": ServicePrices.ESIM_ATT_3,
        "6": ServicePrices.ESIM_ATT_6,
    },
    "tmobile": {
        "1": ServicePrices.ESIM_TMOBILE,
        "3": ServicePrices.ESIM_TMOBILE_3,
        "6": ServicePrices.ESIM_TMOBILE_6,
    }
}


# ═══════════════════════════════════════════════════════════════════════
# DB helpers for eSIM SMS / Data categories
# ═══════════════════════════════════════════════════════════════════════

async def _load_esim_items(session: AsyncSession, category_code: str) -> list[AccountItem]:
    result = await session.execute(
        select(AccountItem)
        .where(AccountItem.category_code == category_code, AccountItem.is_active == True)
        .order_by(AccountItem.position, AccountItem.id)
    )
    return list(result.scalars().all())


async def _get_esim_inventory_count(session: AsyncSession, item_id: int) -> int:
    result = await session.execute(
        select(func.count(AccountInventory.id))
        .where(AccountInventory.item_id == item_id, AccountInventory.is_sold == False)
    )
    return result.scalar() or 0


async def _try_esim_instant_delivery(
    session: AsyncSession, item_id: int | None, quantity: int, user_id: int, order_id: int
) -> list[dict] | None:
    if item_id is None or quantity < 1:
        return None
    result = await session.execute(
        select(AccountInventory)
        .where(AccountInventory.item_id == item_id, AccountInventory.is_sold == False)
        .limit(quantity)
        .with_for_update(skip_locked=True)
    )
    available = result.scalars().all()
    
    if not available:
        return None

    from datetime import datetime, timezone
    delivered = []
    for inv in available:
        inv.is_sold = True
        inv.sold_to_user_id = user_id
        inv.sold_at = datetime.now(timezone.utc)
        inv.order_id = order_id
        delivered.append(inv.credentials)
    await session.flush()
    return delivered


def _esim_catalog_keyboard(items: list[AccountItem], cat_code: str) -> InlineKeyboardMarkup:
    rows = []
    for item in items:
        rows.append([InlineKeyboardButton(
            text=f"{item.name} — ${item.price}",
            callback_data=f"esim_item:{item.id}"
        )])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="esim_back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _esim_item_qty_keyboard(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="2️⃣", callback_data=f"esim_iq:{item_id}:2"),
         InlineKeyboardButton(text=f"3️⃣ (-{BulkDiscounts.ESIM_QTY_3}%)", callback_data=f"esim_iq:{item_id}:3"),
         InlineKeyboardButton(text=f"5️⃣ (-{BulkDiscounts.ESIM_QTY_5}%)", callback_data=f"esim_iq:{item_id}:5")],
        [InlineKeyboardButton(text=f"🔟 (-{BulkDiscounts.ESIM_QTY_10}%)", callback_data=f"esim_iq:{item_id}:10")],
        [InlineKeyboardButton(text="✅ Buy 1 item", callback_data=f"esim_ib:{item_id}:1")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"esim_iback:{item_id}")],
    ])


def _format_creds(c: dict) -> str:
    if "data" in c:
        return str(c["data"])
    return " : ".join(str(v) for v in c.values())


def _md_escape(s: str) -> str:
    """Экранирование для Telegram parse_mode Markdown (имена из БД могут содержать _ * `)."""
    if s is None:
        return ""
    t = str(s)
    return (
        t.replace("\\", "\\\\")
        .replace("_", "\\_")
        .replace("*", "\\*")
        .replace("`", "\\`")
        .replace("[", "\\[")
    )


# ═══════════════════════════════════════════════════════════════════════
# MAIN eSIM MENU
# ═══════════════════════════════════════════════════════════════════════

@router.message(F.text == "📶 eSIM")
async def esim_main_handler(message: Message, texts, buttons):
    try:
        await message.answer_photo(
            photo=ESIM_PHOTO,
            caption=texts.ESIM_MAIN,
            reply_markup=esim_main_keyboard(buttons)
        )
    except Exception:
        await message.answer(texts.ESIM_MAIN, reply_markup=esim_main_keyboard(buttons))


@router.callback_query(F.data == "esim_back_main")
async def esim_back_main_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    await state.clear()
    await safe_edit_message(
        callback,
        texts.ESIM_MAIN,
        reply_markup=esim_main_keyboard(buttons)
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════
# eSIM SMS — DB-driven catalog (AccountCategory "esim_sms")
# ═══════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "esim_sms")
async def esim_sms_catalog(callback: CallbackQuery, session: AsyncSession, state: FSMContext, texts, buttons):
    await state.clear()
    items = await _load_esim_items(session, _ESIM_SMS_CAT)
    if not items:
        await callback.answer("No SMS eSIM items available yet", show_alert=True)
        return
    await safe_edit_message(
        callback,
        texts.ESIM_SMS_SELECT_OPERATOR,
        reply_markup=_esim_catalog_keyboard(items, _ESIM_SMS_CAT)
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════
# eSIM DATA — DB-driven catalog (AccountCategory "esim_data")
# ═══════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "esim_data")
async def esim_data_catalog(callback: CallbackQuery, session: AsyncSession, state: FSMContext, texts, buttons):
    await state.clear()
    items = await _load_esim_items(session, _ESIM_DATA_CAT)
    if not items:
        await callback.answer("No Data eSIM items available yet", show_alert=True)
        return
    await safe_edit_message(
        callback,
        texts.ESIM_DATA_SELECT_OPERATOR,
        reply_markup=_esim_catalog_keyboard(items, _ESIM_DATA_CAT)
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════
# eSIM ITEM DETAIL + QUANTITY + BUY (shared for SMS & Data)
# ═══════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("esim_item:"))
async def esim_item_detail(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    item_id = int(callback.data.split(":")[1])
    result = await session.execute(select(AccountItem).where(AccountItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        await callback.answer("Item not found", show_alert=True)
        return
    if item.category_code not in _ESIM_CATALOG_CATEGORIES:
        await callback.answer("Invalid item", show_alert=True)
        return

    stock = await _get_esim_inventory_count(session, item_id)
    icon = "📞" if item.category_code == _GV_CAT else "📶"
    safe_name = _md_escape(item.name)
    text = (
        f"{icon} *{safe_name}*\n\n"
        f"💵 Price: ${item.price}\n"
        f"🕒 Delivery: 5-10 minutes (auto)\n"
    )
    if stock > 0:
        text += f"\n⚡ *In stock:* {stock} — instant delivery!"
    text += "\n\nSelect quantity or buy 1 item:"

    await safe_edit_message(
        callback, text,
        reply_markup=_esim_item_qty_keyboard(item_id),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("esim_iback:"))
async def esim_item_back(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    item_id = int(callback.data.split(":")[1])
    result = await session.execute(select(AccountItem).where(AccountItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        await callback.answer()
        return
    if item.category_code not in _ESIM_CATALOG_CATEGORIES:
        await safe_edit_message(callback, texts.ESIM_MAIN, reply_markup=esim_main_keyboard(buttons))
        await callback.answer()
        return

    cat_code = item.category_code
    items = await _load_esim_items(session, cat_code)
    if cat_code == _GV_CAT:
        select_text = getattr(texts, "ESIM_GV_SELECT", "📞 Google Voice\n\nChoose a product:")
    elif cat_code == _ESIM_SMS_CAT:
        select_text = texts.ESIM_SMS_SELECT_OPERATOR
    else:
        select_text = texts.ESIM_DATA_SELECT_OPERATOR
    await safe_edit_message(callback, select_text, reply_markup=_esim_catalog_keyboard(items, cat_code))
    await callback.answer()


@router.callback_query(F.data.startswith("esim_ib:") | F.data.startswith("esim_iq:"))
async def esim_item_buy(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    parts = callback.data.split(":")
    item_id = int(parts[1])
    quantity = int(parts[2])

    result = await session.execute(select(AccountItem).where(AccountItem.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        await callback.answer("Item not found", show_alert=True)
        return
    if item.category_code not in _ESIM_CATALOG_CATEGORIES:
        await callback.answer("Invalid item", show_alert=True)
        return

    unit_price = item.price
    discount = ServicePrices.get_bulk_discount(quantity)
    base_price = Decimal(str(unit_price)) * quantity
    total_price = (base_price * (Decimal("1") - discount)).quantize(Decimal("0.01"))
    discount_percent = float(discount * 100)

    pricing = await OrderService.get_order_pricing(
        session,
        user_id=callback.from_user.id,
        category="esim",
        service_name=item.code,
        amount=total_price,
    )

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    if not user or user.balance < pricing.final_amount:
        await callback.answer(
            texts.INSUFFICIENT_BALANCE_DETAILED.format(
                required=pricing.final_amount,
                balance=user.balance if user else 0
            ),
            show_alert=True
        )
        return

    if quantity > 1:
        confirm_text = f"{texts.BULK_PURCHASE_TITLE}\n\n"
        confirm_text += f"{texts.BULK_PURCHASE_WARNING}\n\n"
        confirm_text += texts.BULK_PURCHASE_PRODUCT.format(product_name=item.name) + "\n"
        confirm_text += texts.BULK_PURCHASE_QUANTITY.format(quantity=quantity) + "\n"
        confirm_text += texts.BULK_PURCHASE_UNIT_PRICE.format(unit_price=unit_price) + "\n"
        if discount_percent > 0:
            confirm_text += texts.BULK_PURCHASE_DISCOUNT.format(discount_percent=discount_percent) + "\n"
        confirm_text += texts.BULK_PURCHASE_TOTAL.format(total_price=pricing.final_amount) + "\n\n"
        confirm_text += texts.BULK_PURCHASE_BALANCE.format(balance=user.balance) + "\n"
        new_balance = user.balance - pricing.final_amount
        confirm_text += texts.BULK_PURCHASE_NEW_BALANCE.format(new_balance=new_balance) + "\n\n"
        confirm_text += texts.BULK_PURCHASE_CONFIRM_TEXT.format(quantity=quantity, total_price=pricing.final_amount)

        await state.update_data(
            esim_item_id=item_id,
            esim_item_code=item.code,
            esim_item_name=item.name,
            quantity=quantity,
            unit_price=float(unit_price),
            total_price=float(pricing.final_amount),
            original_price=float(pricing.original_amount),
            coupon_code=pricing.code,
            discount_amount=float(pricing.discount_amount),
            discount_percent=discount_percent,
            checkout_category="esim",
            checkout_service_name=item.code,
            checkout_base_price=str(total_price),
            checkout_confirm_text=confirm_text,
            checkout_keyboard_type="custom",
            checkout_confirm_callback="confirm_bulk_esim",
            checkout_cancel_callback="cancel_bulk_esim",
            checkout_parse_mode="Markdown",
            selected_coupon_code=pricing.code,
            selected_user_coupon_id=None,
        )
        await state.set_state(ESIMStates.confirm_bulk_purchase)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=texts.CONFIRM_PURCHASE, callback_data="confirm_bulk_esim")],
            [InlineKeyboardButton(text=texts.CANCEL_PURCHASE, callback_data="cancel_bulk_esim")]
        ])
        await safe_edit_message(callback, confirm_text, reply_markup=keyboard, parse_mode="Markdown")
        return

    success = await OrderService.deduct_balance(session, callback.from_user.id, pricing.final_amount)
    if not success:
        await callback.answer(
            texts.INSUFFICIENT_BALANCE_DETAILED.format(required=f"{pricing.final_amount:.2f}", balance=user.balance if user else 0),
            show_alert=True,
        )
        return

    order = await OrderService.create_order(
        session,
        user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
        category="esim",
        service_name=item.code,
        input_data={"item_id": item_id, "item_name": item.name, "quantity": 1},
        price=pricing.final_amount,
        original_price=pricing.original_amount,
        coupon_code=pricing.code,
        discount_amount=pricing.discount_amount,
        coupon_application=pricing,
    )

    delivered = await _try_esim_instant_delivery(session, item_id, 1, callback.from_user.id, order.id)
    
    if delivered:
        order.status = "completed"
        order.result_data = {"instant_delivery": True, "delivered_count": len(delivered)}
    
    await session.commit()

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    eta = ServiceETA.get_eta("esim")
    ok_icon = "📞" if item.category_code == _GV_CAT else "📶"
    safe_name = _md_escape(item.name)

    if delivered:
        creds_text = "\n".join(f"  {i+1}. {_format_creds(c)}" for i, c in enumerate(delivered))
        await safe_edit_message(
            callback,
            f"✅ *Order #{order.id} — Instant Delivery!*\n\n"
            f"{ok_icon} *{safe_name}*\n"
            f"💰 *Paid:* ${pricing.final_amount}\n"
            f"💳 *Balance:* ${user.balance:.2f}\n\n"
            f"🔑 *Your credentials:*\n```\n{creds_text}\n```\n\n"
            f"⚠️ Save this message — it won't be shown again.",
            parse_mode="Markdown",
        )
    else:
        await safe_edit_message(
            callback,
            texts.ORDER_CREATED.format(
                product=item.name,
                price=order.price,
                balance=user.balance,
                eta=eta
            ),
            parse_mode="Markdown"
        )
    await callback.answer(texts.ORDER_CREATED_ALERT)


@router.callback_query(F.data == "confirm_bulk_esim")
async def confirm_bulk_esim_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    data = await state.get_data()

    item_id = data.get("esim_item_id")
    item_code = data.get("esim_item_code", "")
    item_name = data.get("esim_item_name", "eSIM")
    quantity = data.get("quantity", 1)

    if item_id is None:
        await callback.answer(
            getattr(texts, "SESSION_EXPIRED_RETRY", "Session expired. Please start again."),
            show_alert=True,
        )
        await state.clear()
        return

    chk = await session.execute(select(AccountItem).where(AccountItem.id == item_id))
    chk_item = chk.scalar_one_or_none()
    if not chk_item or chk_item.category_code not in _ESIM_CATALOG_CATEGORIES:
        await callback.answer("Invalid or expired item", show_alert=True)
        await state.clear()
        return

    pricing = await CheckoutCouponService.get_checkout_pricing(
        session,
        telegram_user_id=callback.from_user.id,
        state_data=data,
    )

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    if not user or user.balance < pricing.final_amount:
        await callback.answer(
            texts.INSUFFICIENT_BALANCE_DETAILED.format(required=f"{pricing.final_amount:.2f}", balance=user.balance if user else 0),
            show_alert=True
        )
        await state.clear()
        return

    success = await OrderService.deduct_balance(session, callback.from_user.id, pricing.final_amount)
    if not success:
        await callback.answer(
            texts.INSUFFICIENT_BALANCE_DETAILED.format(required=f"{pricing.final_amount:.2f}", balance=user.balance if user else 0),
            show_alert=True,
        )
        await state.clear()
        return

    order = await OrderService.create_order(
        session,
        user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
        category="esim",
        service_name=item_code,
        input_data={"item_id": item_id, "item_name": item_name, "quantity": quantity},
        price=pricing.final_amount,
        original_price=pricing.original_amount,
        coupon_code=pricing.code,
        discount_amount=pricing.discount_amount,
        coupon_application=pricing,
    )

    ok_icon = "📞" if chk_item.category_code == _GV_CAT else "📶"

    delivered = await _try_esim_instant_delivery(session, item_id, quantity, callback.from_user.id, order.id)
    
    if delivered:
        order.status = "completed"
        order.result_data = {"instant_delivery": True, "delivered_count": len(delivered)}
    
    await session.commit()

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    eta = ServiceETA.get_eta("esim")
    product_display = f"{item_name} x{quantity}" if quantity > 1 else item_name
    safe_product = _md_escape(product_display)

    if delivered:
        creds_text = "\n".join(f"  {i+1}. {_format_creds(c)}" for i, c in enumerate(delivered))
        await safe_edit_message(
            callback,
            f"✅ *Order #{order.id} — Instant Delivery!*\n\n"
            f"{ok_icon} *{safe_product}*\n"
            f"💰 *Paid:* ${pricing.final_amount}\n"
            f"💳 *Balance:* ${user.balance:.2f}\n\n"
            f"🔑 *Your credentials:*\n```\n{creds_text}\n```\n\n"
            f"⚠️ Save this message — it won't be shown again.",
            parse_mode="Markdown",
        )
    else:
        await safe_edit_message(
            callback,
            texts.ORDER_CREATED.format(
                product=product_display,
                price=order.price,
                balance=user.balance,
                eta=eta
            ),
            parse_mode="Markdown"
        )
    await state.clear()
    await callback.answer(texts.ORDER_CREATED_ALERT)


@router.callback_query(F.data == "cancel_bulk_esim")
async def cancel_bulk_esim_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    await state.clear()
    await safe_edit_message(
        callback,
        texts.PURCHASE_CANCELLED + "\n\n" + texts.ESIM_MAIN,
        reply_markup=esim_main_keyboard(buttons)
    )
    await callback.answer(texts.PURCHASE_CANCELLED)


# ═══════════════════════════════════════════════════════════════════════
# GOOGLE VOICE — только каталог из БД (AccountItem, category "gv"), без штатов
# ═══════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "esim_gv")
async def gv_catalog(callback: CallbackQuery, session: AsyncSession, state: FSMContext, texts, buttons):
    await state.clear()
    items = await _load_esim_items(session, _GV_CAT)
    if not items:
        await callback.answer("No Google Voice items available yet", show_alert=True)
        return
    header = getattr(texts, "ESIM_GV_SELECT", "📞 Google Voice\n\nChoose a product:")
    await safe_edit_message(
        callback,
        header,
        reply_markup=_esim_catalog_keyboard(items, _GV_CAT),
    )
    await callback.answer()


# ═══════════════════════════════════════════════════════════════════════
# eSIM CONFIGURATOR (with CS/CR)
# ═══════════════════════════════════════════════════════════════════════

def _esim_cfg_operator_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📶 AT&T", callback_data="esim_cfg_op:att")],
        [InlineKeyboardButton(text="📶 Verizon", callback_data="esim_cfg_op:verizon")],
        [InlineKeyboardButton(text="📶 T-Mobile", callback_data="esim_cfg_op:tmobile")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="esim_back_main")],
    ])


def _esim_cfg_states_keyboard(page=0):
    from mirror_bot.constants.states_data import STATES_PAGES

    keyboard_buttons = []
    keyboard_buttons.append([InlineKeyboardButton(text="🎲 ANY STATE — $0", callback_data="esim_cfg_state:ANY")])

    current_page = STATES_PAGES[page]
    states_row = []
    for i, (name, code) in enumerate(current_page, 1):
        states_row.append(InlineKeyboardButton(
            text=f"{name}, {code}",
            callback_data=f"esim_cfg_state:{code}"
        ))
        if i % 3 == 0:
            keyboard_buttons.append(states_row)
            states_row = []
    if states_row:
        keyboard_buttons.append(states_row)

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"esim_cfg_state_page:{page-1}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page+1}/4", callback_data="esim_cfg_noop"))
    if page < 3:
        nav_row.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"esim_cfg_state_page:{page+1}"))
    keyboard_buttons.append(nav_row)
    keyboard_buttons.append([InlineKeyboardButton(text="⬅️ Back", callback_data="esim_cfg_back_op")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


def _esim_cfg_cs_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⭐ 800+ — +${ServicePrices.ESIM_CFG_CS_800_PLUS}", callback_data="esim_cfg_cs:800+")],
        [InlineKeyboardButton(text=f"✨ 700+ — +${ServicePrices.ESIM_CFG_CS_700_PLUS}", callback_data="esim_cfg_cs:700+")],
        [InlineKeyboardButton(text="📊 ANY — $0", callback_data="esim_cfg_cs:any")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="esim_cfg_back_state")],
    ])


def _esim_cfg_report_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💼 Basic — ${ServicePrices.ESIM_CFG_REPORT_BASIC}", callback_data="esim_cfg_report:basic")],
        [InlineKeyboardButton(text=f"📘 With CR — +${ServicePrices.ESIM_CFG_REPORT_CR}", callback_data="esim_cfg_report:cr")],
        [InlineKeyboardButton(text=f"🪪 CR & DL — +${ServicePrices.ESIM_CFG_REPORT_CR_DL}", callback_data="esim_cfg_report:cr_dl")],
        [InlineKeyboardButton(text=f"🛰️ CR, DL & MVR — +${ServicePrices.ESIM_CFG_REPORT_CR_DL_MVR}", callback_data="esim_cfg_report:cr_dl_mvr")],
        [InlineKeyboardButton(text=f"🏁 CR, DL & FULL MVR — +${ServicePrices.ESIM_CFG_REPORT_CR_DL_FULLMVR}", callback_data="esim_cfg_report:full")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="esim_cfg_back_cs")],
    ])


def _calculate_esim_cfg_price(config: dict) -> Decimal:
    operator = config.get("cfg_operator", "att")
    base = OPERATOR_PRICES.get(operator, {}).get("1", ServicePrices.ESIM_ATT)
    price = Decimal(str(base))

    if config.get("cfg_state", "ANY") != "ANY":
        price += ServicePrices.ESIM_CFG_STATE_SURCHARGE

    cs = config.get("cfg_cs", "any")
    price += {
        "800+": ServicePrices.ESIM_CFG_CS_800_PLUS,
        "700+": ServicePrices.ESIM_CFG_CS_700_PLUS,
    }.get(cs, Decimal("0"))

    report = config.get("cfg_report", "basic")
    price += {
        "basic": ServicePrices.ESIM_CFG_REPORT_BASIC,
        "cr": ServicePrices.ESIM_CFG_REPORT_CR,
        "cr_dl": ServicePrices.ESIM_CFG_REPORT_CR_DL,
        "cr_dl_mvr": ServicePrices.ESIM_CFG_REPORT_CR_DL_MVR,
        "full": ServicePrices.ESIM_CFG_REPORT_CR_DL_FULLMVR,
    }.get(report, Decimal("0"))

    return price


@router.callback_query(F.data == "esim_configurator")
async def esim_cfg_main(callback: CallbackQuery, state: FSMContext, texts, buttons):
    await state.clear()
    await safe_edit_message(
        callback,
        "⚙️ *eSIM Configurator*\n\n"
        "Build your custom eSIM order step by step.\n\n"
        "1️⃣ Select operator\n"
        "2️⃣ Select state\n"
        "3️⃣ Credit Score\n"
        "4️⃣ Report type\n\n"
        "Choose operator:",
        reply_markup=_esim_cfg_operator_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("esim_cfg_op:"))
async def esim_cfg_operator_selected(callback: CallbackQuery, state: FSMContext, texts, buttons):
    operator = callback.data.split(":")[1]
    base_price = OPERATOR_PRICES.get(operator, {}).get("1", ServicePrices.ESIM_ATT)
    await state.update_data(cfg_operator=operator)
    await state.set_state(ESIMConfigStates.selecting_state)
    await safe_edit_message(
        callback,
        f"⚙️ *eSIM Configurator*\n\n"
        f"📶 *Operator:* {operator.upper()}\n"
        f"💰 *Base price:* ${base_price}\n\n"
        f"📍 Select state (specific state +${ServicePrices.ESIM_CFG_STATE_SURCHARGE}):",
        reply_markup=_esim_cfg_states_keyboard(0),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("esim_cfg_state_page:"))
async def esim_cfg_state_page(callback: CallbackQuery, state: FSMContext, texts, buttons):
    page = int(callback.data.split(":")[1])
    data = await state.get_data()
    operator = data.get("cfg_operator", "att")
    base_price = OPERATOR_PRICES.get(operator, {}).get("1", ServicePrices.ESIM_ATT)
    await safe_edit_message(
        callback,
        f"⚙️ *eSIM Configurator*\n\n"
        f"📶 *Operator:* {operator.upper()}\n"
        f"💰 *Base price:* ${base_price}\n\n"
        f"📍 Select state (specific state +${ServicePrices.ESIM_CFG_STATE_SURCHARGE}):",
        reply_markup=_esim_cfg_states_keyboard(page),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("esim_cfg_state:"))
async def esim_cfg_state_selected(callback: CallbackQuery, state: FSMContext, texts, buttons):
    state_code = callback.data.split(":")[1]
    await state.update_data(cfg_state=state_code)
    await state.set_state(ESIMConfigStates.selecting_cs)

    data = await state.get_data()
    operator = data.get("cfg_operator", "att")
    state_label = "Any State" if state_code == "ANY" else state_code

    await safe_edit_message(
        callback,
        f"⚙️ *eSIM Configurator*\n\n"
        f"📶 *Operator:* {operator.upper()}\n"
        f"📍 *State:* {state_label}\n\n"
        f"📊 Select Credit Score:",
        reply_markup=_esim_cfg_cs_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("esim_cfg_cs:"))
async def esim_cfg_cs_selected(callback: CallbackQuery, state: FSMContext, texts, buttons):
    cs = callback.data.split(":")[1]
    await state.update_data(cfg_cs=cs)
    await state.set_state(ESIMConfigStates.selecting_report)

    data = await state.get_data()
    operator = data.get("cfg_operator", "att")
    state_code = data.get("cfg_state", "ANY")
    state_label = "Any State" if state_code == "ANY" else state_code
    cs_label = cs.upper() if cs != "any" else "Any"

    await safe_edit_message(
        callback,
        f"⚙️ *eSIM Configurator*\n\n"
        f"📶 *Operator:* {operator.upper()}\n"
        f"📍 *State:* {state_label}\n"
        f"📊 *CS:* {cs_label}\n\n"
        f"📋 Select report type:",
        reply_markup=_esim_cfg_report_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


def _esim_cfg_qty_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1", callback_data="esim_cfg_qty:1"),
         InlineKeyboardButton(text=f"3 (-{BulkDiscounts.ESIM_QTY_3}%)", callback_data="esim_cfg_qty:3"),
         InlineKeyboardButton(text=f"5 (-{BulkDiscounts.ESIM_QTY_5}%)", callback_data="esim_cfg_qty:5")],
        [InlineKeyboardButton(text=f"🔟 (-{BulkDiscounts.ESIM_QTY_10}%)", callback_data="esim_cfg_qty:10")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="esim_cfg_back_report")],
    ])


def _esim_cfg_summary(data: dict) -> str:
    operator = data.get("cfg_operator", "att")
    state_code = data.get("cfg_state", "ANY")
    state_label = "Any State" if state_code == "ANY" else state_code
    cs = data.get("cfg_cs", "any")
    cs_label = cs.upper() if cs != "any" else "Any"
    report = data.get("cfg_report", "basic")
    report_labels = {
        "basic": "Basic", "cr": "With CR", "cr_dl": "CR & DL",
        "cr_dl_mvr": "CR, DL & MVR", "full": "CR, DL & FULL MVR",
    }
    report_label = report_labels.get(report, report)
    return (
        f"📶 *Operator:* {operator.upper()}\n"
        f"📍 *State:* {state_label}\n"
        f"📊 *CS:* {cs_label}\n"
        f"📋 *Report:* {report_label}"
    )


@router.callback_query(F.data.startswith("esim_cfg_report:"))
async def esim_cfg_report_selected(callback: CallbackQuery, state: FSMContext, texts, buttons):
    report = callback.data.split(":")[1]
    await state.update_data(cfg_report=report)
    await state.set_state(ESIMConfigStates.selecting_qty)

    data = await state.get_data()
    unit_price = _calculate_esim_cfg_price(data)

    await safe_edit_message(
        callback,
        f"⚙️ *eSIM Configurator*\n\n"
        f"{_esim_cfg_summary(data)}\n\n"
        f"💰 *Unit price:* ${unit_price}\n\n"
        f"📦 Select quantity:",
        reply_markup=_esim_cfg_qty_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("esim_cfg_qty:"))
async def esim_cfg_qty_selected(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    quantity = int(callback.data.split(":")[1])
    await state.update_data(cfg_quantity=quantity)
    await state.set_state(ESIMConfigStates.confirmation)

    data = await state.get_data()
    unit_price = _calculate_esim_cfg_price(data)
    discount = ServicePrices.get_bulk_discount(quantity)
    total = (unit_price * quantity * (Decimal("1") - discount)).quantize(Decimal("0.01"))
    discount_pct = float(discount * 100)

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)

    confirm_text = (
        f"✅ *Confirm your order*\n\n"
        f"⚙️ *eSIM Configurator*\n"
        f"{_esim_cfg_summary(data)}\n\n"
        f"📦 *Quantity:* {quantity}\n"
        f"💰 *Unit price:* ${unit_price}\n"
    )
    if discount_pct > 0:
        confirm_text += f"🏷 *Discount:* -{discount_pct:.0f}%\n"
    confirm_text += (
        f"💰 *Total:* ${total}\n"
        f"💳 *Your balance:* ${user.balance:.2f}\n"
        f"💳 *After payment:* ${user.balance - total:.2f}\n\n"
        f"⏱ *ETA:* {ServiceETA.get_eta('esim')}"
    )

    await safe_edit_message(
        callback,
        confirm_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Confirm", callback_data="esim_cfg_confirm_yes")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="esim_cfg_confirm_no")],
        ]),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "esim_cfg_confirm_yes", ESIMConfigStates.confirmation)
async def esim_cfg_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    data = await state.get_data()
    unit_price = _calculate_esim_cfg_price(data)
    quantity = data.get("cfg_quantity", 1)
    discount = ServicePrices.get_bulk_discount(quantity)
    total = (unit_price * quantity * (Decimal("1") - discount)).quantize(Decimal("0.01"))

    operator = data.get("cfg_operator", "att")
    state_code = data.get("cfg_state", "ANY")
    cs = data.get("cfg_cs", "any")
    report = data.get("cfg_report", "basic")

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    if not user or user.balance < total:
        await callback.answer("Insufficient balance", show_alert=True)
        await state.clear()
        return

    success = await OrderService.deduct_balance(session, callback.from_user.id, total)
    if not success:
        await callback.answer("Insufficient balance", show_alert=True)
        await state.clear()
        return

    service_name = f"esim_cfg_{operator}_{state_code.lower()}"
    order = await OrderService.create_order(
        session,
        user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
        category="esim",
        service_name=service_name,
        input_data={
            "type": "configurator",
            "operator": operator,
            "state": state_code,
            "credit_score": cs,
            "report": report,
            "quantity": quantity,
        },
        price=total,
    )

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    state_label = "Any State" if state_code == "ANY" else state_code
    qty_text = f" x{quantity}" if quantity > 1 else ""
    await state.clear()

    await safe_edit_message(
        callback,
        f"✅ *Order #{order.id} created!*\n\n"
        f"⚙️ *eSIM* — {operator.upper()} / {state_label}{qty_text}\n"
        f"💰 *Paid:* ${total}\n"
        f"💳 *Balance:* ${user.balance:.2f}\n\n"
        f"⏱ *ETA:* {ServiceETA.get_eta('esim')}\n"
        f"📬 You'll receive the result here when ready.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")]
        ]),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "esim_cfg_confirm_no", ESIMConfigStates.confirmation)
async def esim_cfg_cancel(callback: CallbackQuery, state: FSMContext, texts, buttons):
    await state.clear()
    await safe_edit_message(
        callback,
        "❌ Order cancelled.\n\n" + texts.ESIM_MAIN,
        reply_markup=esim_main_keyboard(buttons),
    )
    await callback.answer()


@router.callback_query(F.data == "esim_cfg_back_op")
async def esim_cfg_back_to_operator(callback: CallbackQuery, state: FSMContext, texts, buttons):
    await state.clear()
    await safe_edit_message(
        callback,
        "⚙️ *eSIM Configurator*\n\nChoose operator:",
        reply_markup=_esim_cfg_operator_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "esim_cfg_back_state")
async def esim_cfg_back_to_state(callback: CallbackQuery, state: FSMContext, texts, buttons):
    data = await state.get_data()
    operator = data.get("cfg_operator", "att")
    base_price = OPERATOR_PRICES.get(operator, {}).get("1", ServicePrices.ESIM_ATT)
    await state.set_state(ESIMConfigStates.selecting_state)
    await safe_edit_message(
        callback,
        f"⚙️ *eSIM Configurator*\n\n"
        f"📶 *Operator:* {operator.upper()}\n"
        f"💰 *Base price:* ${base_price}\n\n"
        f"📍 Select state (specific state +${ServicePrices.ESIM_CFG_STATE_SURCHARGE}):",
        reply_markup=_esim_cfg_states_keyboard(0),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "esim_cfg_back_report")
async def esim_cfg_back_to_report(callback: CallbackQuery, state: FSMContext, texts, buttons):
    data = await state.get_data()
    operator = data.get("cfg_operator", "att")
    state_code = data.get("cfg_state", "ANY")
    state_label = "Any State" if state_code == "ANY" else state_code
    cs = data.get("cfg_cs", "any")
    cs_label = cs.upper() if cs != "any" else "Any"
    await state.set_state(ESIMConfigStates.selecting_report)
    await safe_edit_message(
        callback,
        f"⚙️ *eSIM Configurator*\n\n"
        f"📶 *Operator:* {operator.upper()}\n"
        f"📍 *State:* {state_label}\n"
        f"📊 *CS:* {cs_label}\n\n"
        f"📋 Select report type:",
        reply_markup=_esim_cfg_report_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "esim_cfg_back_cs")
async def esim_cfg_back_to_cs(callback: CallbackQuery, state: FSMContext, texts, buttons):
    data = await state.get_data()
    operator = data.get("cfg_operator", "att")
    state_code = data.get("cfg_state", "ANY")
    state_label = "Any State" if state_code == "ANY" else state_code
    await state.set_state(ESIMConfigStates.selecting_cs)
    await safe_edit_message(
        callback,
        f"⚙️ *eSIM Configurator*\n\n"
        f"📶 *Operator:* {operator.upper()}\n"
        f"📍 *State:* {state_label}\n\n"
        f"📊 Select Credit Score:",
        reply_markup=_esim_cfg_cs_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "esim_cfg_noop")
async def esim_cfg_noop(callback: CallbackQuery):
    await callback.answer()
