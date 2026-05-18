from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from decimal import Decimal
from datetime import datetime, timezone
from mirror_bot.keyboards.inline import InlineKeyboardMarkup, InlineKeyboardButton
from mirror_bot.services.order_service import OrderService
from mirror_bot.services.checkout_coupon_service import CheckoutCouponService
from mirror_bot.services.user_service import UserService
from mirror_bot.constants.buttons_en import ButtonTexts
from mirror_bot.utils.message_utils import safe_edit_message
from mirror_bot.constants.prices import BulkDiscounts
from mirror_bot.constants.service_eta import ServiceETA
from mirror_bot.services.menu_counts_service import MenuCountService
from shared.database.models import AccountCategory, AccountItem, AccountInventory
from mirror_bot.states.accounts import AccountStates
from mirror_bot.utils.media_library import resolve_bot_photo

router = Router()

ACCOUNTS_PHOTO = resolve_bot_photo("accounts", fallback_path="media/Accounts.jpg")
ITEMS_PER_PAGE = 5


async def _get_active_categories(session: AsyncSession) -> list[AccountCategory]:
    result = await session.execute(
        select(AccountCategory)
        .where(AccountCategory.is_active == True)
        .order_by(AccountCategory.position, AccountCategory.id)
    )
    return list(result.scalars().all())


async def _get_category_items(session: AsyncSession, category_code: str) -> list[AccountItem]:
    result = await session.execute(
        select(AccountItem)
        .where(AccountItem.category_code == category_code, AccountItem.is_active == True)
        .order_by(AccountItem.position, AccountItem.id)
    )
    return list(result.scalars().all())


async def _get_item_by_id(session: AsyncSession, item_id: int) -> AccountItem | None:
    result = await session.execute(select(AccountItem).where(AccountItem.id == item_id))
    return result.scalar_one_or_none()


async def _get_inventory_count(session: AsyncSession, item_id: int) -> int:
    result = await session.execute(
        select(func.count(AccountInventory.id))
        .where(AccountInventory.item_id == item_id, AccountInventory.is_sold == False)
    )
    return result.scalar() or 0


async def _try_instant_delivery(session: AsyncSession, item_id: int, quantity: int, user_id: int, order_id: int) -> list[dict]:
    """Deliver as many items from inventory as possible. Returns list of delivered credentials (may be shorter than quantity)."""
    result = await session.execute(
        select(AccountInventory)
        .where(AccountInventory.item_id == item_id, AccountInventory.is_sold == False)
        .limit(quantity)
        .with_for_update(skip_locked=True)
    )
    available = result.scalars().all()

    delivered = []
    for inv in available:
        inv.is_sold = True
        inv.sold_to_user_id = user_id
        inv.sold_at = datetime.now(timezone.utc)
        inv.order_id = order_id
        delivered.append(inv.credentials)
    if delivered:
        await session.flush()
    return delivered


# ── Keyboards ────────────────────────────────────────────────────────────────

def accounts_main_keyboard(buttons, categories: list[AccountCategory], counts=None):
    counts = counts or {}
    rows = []
    for cat in categories:
        label = ButtonTexts.with_count(cat.name, counts.get(cat.code))
        rows.append([InlineKeyboardButton(text=label, callback_data=f"acc_cat:{cat.code}")])
    rows.append([InlineKeyboardButton(text=buttons.BACK, callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def accounts_catalog_keyboard(
    category_code: str,
    items: list[AccountItem],
    page: int = 0,
    buttons=None,
) -> InlineKeyboardMarkup:
    total_pages = max(1, (len(items) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    start = page * ITEMS_PER_PAGE
    end = min(start + ITEMS_PER_PAGE, len(items))
    rows = []
    for item in items[start:end]:
        rows.append([InlineKeyboardButton(
            text=f"{item.name} | ${item.price}",
            callback_data=f"acc_item:{item.id}"
        )])
    if total_pages > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(
                text=buttons.PREV_PAGE if buttons else "⬅️ Prev",
                callback_data=f"acc_page:{category_code}:{page - 1}"
            ))
        nav.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="page_info"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton(
                text=buttons.NEXT_PAGE if buttons else "Next ➡️",
                callback_data=f"acc_page:{category_code}:{page + 1}"
            ))
        rows.append(nav)
    back_text = buttons.BACK_TO_CATEGORIES if buttons else "🏠 Back"
    rows.append([InlineKeyboardButton(text=back_text, callback_data="accounts_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def account_item_keyboard(item_id: int, category_code: str, buttons):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.get_qty_button(2, 0), callback_data=f"acc_buy:{item_id}:2"),
         InlineKeyboardButton(text=buttons.get_qty_button(3, BulkDiscounts.BANKS_QTY_3), callback_data=f"acc_buy:{item_id}:3"),
         InlineKeyboardButton(text=buttons.get_qty_button(5, BulkDiscounts.BANKS_QTY_5), callback_data=f"acc_buy:{item_id}:5"),
         InlineKeyboardButton(text=buttons.get_qty_button(10, BulkDiscounts.BANKS_QTY_10), callback_data=f"acc_buy:{item_id}:10")],
        [InlineKeyboardButton(text=buttons.CUSTOM_QUANTITY, callback_data=f"acc_custom:{item_id}")],
        [InlineKeyboardButton(text=buttons.BUY_1_ITEM, callback_data=f"acc_buy:{item_id}:1")],
        [InlineKeyboardButton(text=buttons.BACK_TO_LIST, callback_data=f"acc_cat:{category_code}")]
    ])


# ── Handlers ─────────────────────────────────────────────────────────────────

@router.message(F.text.in_(ButtonTexts.get_all_variants("SUBSCRIPTIONS_ACCOUNTS")))
async def accounts_main_handler(message: Message, session: AsyncSession, texts, buttons):
    counts = await MenuCountService.get_accounts_counts(session)
    categories = await _get_active_categories(session)
    kb = accounts_main_keyboard(buttons, categories, counts.get("by_category"))
    try:
        await message.answer_photo(
            photo=ACCOUNTS_PHOTO,
            caption=texts.ACCOUNTS_MAIN,
            reply_markup=kb,
        )
    except Exception:
        await message.answer(texts.ACCOUNTS_MAIN, reply_markup=kb)


@router.callback_query(F.data == "accounts_main")
async def accounts_main_callback(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    counts = await MenuCountService.get_accounts_counts(session)
    categories = await _get_active_categories(session)
    kb = accounts_main_keyboard(buttons, categories, counts.get("by_category"))
    try:
        await callback.message.delete()
        await callback.bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=ACCOUNTS_PHOTO,
            caption=texts.ACCOUNTS_MAIN,
            reply_markup=kb,
        )
    except Exception:
        await safe_edit_message(callback, texts.ACCOUNTS_MAIN, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("acc_cat:"))
async def accounts_category_handler(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    category_code = callback.data.split(":")[1]
    items = await _get_category_items(session, category_code)
    cat_result = await session.execute(
        select(AccountCategory).where(AccountCategory.code == category_code)
    )
    cat = cat_result.scalar_one_or_none()
    category_name = cat.name if cat else category_code.title()

    if not items:
        await callback.answer("No items in this category yet", show_alert=True)
        return

    select_text = getattr(texts, "BANKS_SELECT_ITEM", "Select item in {category_name}:").format(category_name=category_name)
    await safe_edit_message(
        callback,
        select_text,
        reply_markup=accounts_catalog_keyboard(category_code, items, page=0, buttons=buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("acc_page:"))
async def accounts_page_handler(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    parts = callback.data.split(":")
    category_code = parts[1]
    page = int(parts[2])
    items = await _get_category_items(session, category_code)

    if not items:
        await callback.answer("No items in this category yet", show_alert=True)
        return

    cat_result = await session.execute(
        select(AccountCategory).where(AccountCategory.code == category_code)
    )
    cat = cat_result.scalar_one_or_none()
    category_name = cat.name if cat else category_code.title()

    select_text = getattr(texts, "BANKS_SELECT_ITEM", "Select item in {category_name}:").format(category_name=category_name)
    await safe_edit_message(
        callback,
        select_text,
        reply_markup=accounts_catalog_keyboard(category_code, items, page=page, buttons=buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("acc_item:"))
async def account_item_detail(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    item_id = int(callback.data.split(":")[1])
    item = await _get_item_by_id(session, item_id)
    if not item:
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return

    stock = await _get_inventory_count(session, item.id)

    product_data = texts.PRODUCT_DATA.get(item.code)
    if product_data:
        text = texts.PRODUCT_DESCRIPTION_TEMPLATE.format(
            product_name=item.name,
            category=product_data['category'],
            price=str(item.price),
            delivery=product_data['delivery'],
            description=product_data['description'],
            tutorial_link=product_data['tutorial']
        )
    else:
        text = texts.PRODUCT_DESCRIPTION_TEMPLATE.format(
            product_name=item.name,
            category=getattr(texts, 'PREMIUM_SERVICE', "Product"),
            price=str(item.price),
            delivery="1-6 " + getattr(texts, 'HOURS', "hours"),
            description=item.description or getattr(texts, 'PREMIUM_SERVICE', "Premium service"),
            tutorial_link="#"
        )

    if stock > 0:
        text += f"\n\n⚡ *In stock:* {stock} — instant delivery!"

    await safe_edit_message(
        callback,
        text,
        reply_markup=account_item_keyboard(item.id, item.category_code, buttons),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("acc_buy:"))
async def account_buy_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext, mirror_bot_id: int, texts, buttons):
    parts = callback.data.split(":")
    item_id = int(parts[1])
    quantity = int(parts[2])

    item = await _get_item_by_id(session, item_id)
    if not item:
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return

    base_price = Decimal(str(item.price)) * quantity
    discount_percent = BulkDiscounts.get_bank_discount(quantity)
    total_price = base_price * (Decimal('1') - Decimal(str(discount_percent)) / Decimal('100'))

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)

    confirm_text = f"{texts.BULK_PURCHASE_TITLE}\n\n"
    confirm_text += f"{texts.BULK_PURCHASE_WARNING}\n\n"
    confirm_text += texts.BULK_PURCHASE_PRODUCT.format(product_name=item.name) + "\n"
    confirm_text += texts.BULK_PURCHASE_QUANTITY.format(quantity=quantity) + "\n"
    confirm_text += texts.BULK_PURCHASE_UNIT_PRICE.format(unit_price=item.price) + "\n"
    if discount_percent > 0:
        confirm_text += texts.BULK_PURCHASE_DISCOUNT.format(discount_percent=discount_percent) + "\n"
    confirm_text += texts.BULK_PURCHASE_TOTAL.format(total_price=total_price) + "\n\n"
    confirm_text += texts.BULK_PURCHASE_BALANCE.format(balance=user.balance if user else 0) + "\n"
    new_balance = (user.balance if user else Decimal("0")) - total_price
    confirm_text += texts.BULK_PURCHASE_NEW_BALANCE.format(new_balance=new_balance) + "\n\n"
    confirm_text += texts.BULK_PURCHASE_CONFIRM_TEXT.format(quantity=quantity, total_price=total_price)

    await state.update_data(
        account_item_id=item.id,
        account_code=item.code,
        account_name=item.name,
        account_category_code=item.category_code,
        quantity=quantity,
        unit_price=float(item.price),
        total_price=float(total_price),
        discount_percent=discount_percent,
        checkout_category="accounts",
        checkout_service_name=item.code,
        checkout_base_price=str(total_price),
        checkout_confirm_text=confirm_text,
        checkout_keyboard_type="custom",
        checkout_confirm_callback="confirm_bulk_account",
        checkout_cancel_callback="cancel_bulk_account",
        checkout_parse_mode="Markdown",
        selected_coupon_code=None,
        selected_user_coupon_id=None,
    )
    await state.set_state(AccountStates.confirm_bulk_purchase)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.CONFIRM_PURCHASE, callback_data="confirm_bulk_account")],
        [InlineKeyboardButton(text=texts.CANCEL_PURCHASE, callback_data="cancel_bulk_account")],
    ])
    await safe_edit_message(callback, confirm_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "confirm_bulk_account")
async def confirm_bulk_account_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts):
    data = await state.get_data()

    item_id = data.get('account_item_id')
    quantity = data.get('quantity')
    account_name = data.get('account_name', 'Account')
    account_code = data.get('account_code', '')
    category_code = data.get('account_category_code', '')

    item = await _get_item_by_id(session, item_id) if item_id else None
    if not item:
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        await state.clear()
        return

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    pricing = await CheckoutCouponService.get_checkout_pricing(
        session,
        telegram_user_id=callback.from_user.id,
        state_data=data,
    )
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
            show_alert=True
        )
        await state.clear()
        return

    order = await OrderService.create_order(
        session,
        user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
        category="accounts",
        service_name=account_code,
        input_data={"quantity": quantity, "account_name": account_name},
        price=pricing.final_amount,
        original_price=pricing.original_amount,
        coupon_code=pricing.code,
        discount_amount=pricing.discount_amount,
        coupon_application=pricing,
    )

    delivered = await _try_instant_delivery(session, item.id, quantity, callback.from_user.id, order.id)
    remaining = quantity - len(delivered)

    if remaining == 0:
        order.status = "completed"
        order.result_data = {"instant_delivery": True, "delivered_count": len(delivered)}

    await session.commit()

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)

    eta = ServiceETA.get_eta("account")
    product_display = f"{account_name} x{quantity}" if quantity > 1 else account_name

    def _format_creds(c: dict) -> str:
        if "data" in c:
            return str(c["data"])
        return " : ".join(str(v) for v in c.values())

    if delivered and remaining == 0:
        creds_text = "\n".join(
            f"  {i+1}. {_format_creds(c)}"
            for i, c in enumerate(delivered)
        )
        await safe_edit_message(
            callback,
            f"✅ *Order #{order.id} — Instant Delivery!*\n\n"
            f"📦 *{product_display}*\n"
            f"💰 *Paid:* ${pricing.final_amount}\n"
            f"💳 *Balance:* ${user.balance:.2f}\n\n"
            f"🔑 *Your credentials:*\n```\n{creds_text}\n```\n\n"
            f"⚠️ Save this message — it won't be shown again.",
            parse_mode="Markdown",
        )
    elif delivered and remaining > 0:
        creds_text = "\n".join(
            f"  {i+1}. {_format_creds(c)}"
            for i, c in enumerate(delivered)
        )
        await safe_edit_message(
            callback,
            f"⚡ *Order #{order.id} — Partial Delivery*\n\n"
            f"📦 *{product_display}*\n"
            f"💰 *Paid:* ${pricing.final_amount}\n"
            f"💳 *Balance:* ${user.balance:.2f}\n\n"
            f"🔑 *Delivered instantly ({len(delivered)}/{quantity}):*\n```\n{creds_text}\n```\n\n"
            f"⏳ *Remaining {remaining} pcs* — worker order created, ETA: {eta}\n\n"
            f"⚠️ Save this message — it won't be shown again.",
            parse_mode="Markdown",
        )
    else:
        await safe_edit_message(
            callback,
            texts.ORDER_CREATED.format(
                product=product_display,
                price=pricing.final_amount,
                balance=user.balance,
                eta=eta
            ),
            parse_mode="Markdown"
        )
    await callback.answer(texts.ORDER_CREATED_ALERT)
    await state.clear()


@router.callback_query(F.data == "cancel_bulk_account")
async def cancel_bulk_account_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, texts, buttons):
    await state.clear()
    counts = await MenuCountService.get_accounts_counts(session)
    categories = await _get_active_categories(session)
    kb = accounts_main_keyboard(buttons, categories, counts.get("by_category"))
    await safe_edit_message(
        callback,
        texts.PURCHASE_CANCELLED + "\n\n" + texts.ACCOUNTS_MAIN,
        reply_markup=kb,
    )
    await callback.answer(texts.PURCHASE_CANCELLED)


@router.callback_query(F.data.startswith("acc_custom:"))
async def account_custom_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, texts, buttons):
    item_id = int(callback.data.split(":")[1])

    item = await _get_item_by_id(session, item_id)
    if not item:
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return

    await state.update_data(account_item_id=item.id, account_code=item.code, account_name=item.name, account_category_code=item.category_code)
    await state.set_state(AccountStates.waiting_custom_qty)

    price_text = texts.BANKS_ITEM_PRICE.format(price=item.price)
    discount_text = texts.BANKS_BULK_DISCOUNT.format(
        d3=BulkDiscounts.BANKS_QTY_3,
        d5=BulkDiscounts.BANKS_QTY_5,
        d10=BulkDiscounts.BANKS_QTY_10
    )

    await safe_edit_message(
        callback,
        texts.BANKS_ENTER_QTY.format(
            item_name=f"🧾 {item.name}",
            price_text=price_text,
            discount_text=discount_text,
            enter_quantity=texts.ENTER_QUANTITY
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=buttons.CANCEL, callback_data=f"acc_item:{item.id}")]
        ])
    )
    await callback.answer()


@router.message(AccountStates.waiting_custom_qty, F.text)
async def account_custom_qty_input(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    data = await state.get_data()
    item_id = data.get("account_item_id")

    item = await _get_item_by_id(session, item_id) if item_id else None
    if not item:
        await message.answer(texts.ITEM_NOT_FOUND)
        await state.clear()
        return

    try:
        quantity = int(message.text.strip())

        if quantity < 1 or quantity > 100:
            await message.answer(texts.INVALID_QUANTITY)
            return

        base_price = Decimal(str(item.price)) * quantity
        discount_percent = BulkDiscounts.get_bank_discount(quantity)
        total_price = base_price * (Decimal('1') - Decimal(str(discount_percent)) / Decimal('100'))

        user = await UserService.get_user(session, message.from_user.id, mirror_bot_id)

        confirm_text = f"{texts.BULK_PURCHASE_TITLE}\n\n"
        confirm_text += f"{texts.BULK_PURCHASE_WARNING}\n\n"
        confirm_text += texts.BULK_PURCHASE_PRODUCT.format(product_name=item.name) + "\n"
        confirm_text += texts.BULK_PURCHASE_QUANTITY.format(quantity=quantity) + "\n"
        confirm_text += texts.BULK_PURCHASE_UNIT_PRICE.format(unit_price=item.price) + "\n"
        if discount_percent > 0:
            confirm_text += texts.BULK_PURCHASE_DISCOUNT.format(discount_percent=discount_percent) + "\n"
        confirm_text += texts.BULK_PURCHASE_TOTAL.format(total_price=total_price) + "\n\n"
        confirm_text += texts.BULK_PURCHASE_BALANCE.format(balance=user.balance if user else 0) + "\n"
        new_balance = (user.balance if user else Decimal("0")) - total_price
        confirm_text += texts.BULK_PURCHASE_NEW_BALANCE.format(new_balance=new_balance) + "\n\n"
        confirm_text += texts.BULK_PURCHASE_CONFIRM_TEXT.format(quantity=quantity, total_price=total_price)

        await state.update_data(
            account_item_id=item.id,
            account_code=item.code,
            account_name=item.name,
            account_category_code=item.category_code,
            quantity=quantity,
            unit_price=float(item.price),
            total_price=float(total_price),
            discount_percent=discount_percent,
            checkout_category="accounts",
            checkout_service_name=item.code,
            checkout_base_price=str(total_price),
            checkout_confirm_text=confirm_text,
            checkout_keyboard_type="custom",
            checkout_confirm_callback="confirm_bulk_account",
            checkout_cancel_callback="cancel_bulk_account",
            checkout_parse_mode="Markdown",
            selected_coupon_code=None,
            selected_user_coupon_id=None,
        )
        await state.set_state(AccountStates.confirm_bulk_purchase)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=texts.CONFIRM_PURCHASE, callback_data="confirm_bulk_account")],
            [InlineKeyboardButton(text=texts.CANCEL_PURCHASE, callback_data="cancel_bulk_account")],
        ])
        await message.answer(confirm_text, reply_markup=keyboard, parse_mode="Markdown")
        return

    except ValueError:
        await message.answer(texts.INVALID_FORMAT_NUMBER)


@router.callback_query(F.data == "page_info")
async def page_info_noop_handler(callback: CallbackQuery):
    """No-op handler for page navigation indicator buttons (P1-1 fix)"""
    await callback.answer()

