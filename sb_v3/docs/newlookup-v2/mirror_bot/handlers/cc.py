"""
CC (Credit Cards) — 3-4 категории, товары через seller panel + модерация
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from mirror_bot.keyboards.cc import (
    cc_main_keyboard,
    cc_empty_category_keyboard,
    cc_catalog_keyboard,
    cc_item_detail_keyboard,
    cc_buy_confirm_keyboard,
    cc_result_keyboard,
    cc_specials_keyboard,
    cc_feedback_done_keyboard,
    cc_report_done_keyboard,
)
from mirror_bot.middlewares.language import LanguageHelper
from mirror_bot.constants.buttons_en import ButtonTexts
from mirror_bot.services.order_service import OrderService
from mirror_bot.services.checkout_coupon_service import CheckoutCouponService
from mirror_bot.services.user_service import UserService
from mirror_bot.utils.message_utils import safe_edit_message
from mirror_bot.services.menu_counts_service import MenuCountService
from mirror_bot.utils.media_library import resolve_bot_photo
from mirror_bot.states.order import OrderStates
from mirror_bot.states.cc import CCFilterStates
from shared.database.models import (
    Seller, SellerCCItem, SellerCCOrder,
    SellerSelfregCCItem, SellerCheckItem,
    SellerEnrollItem, SellerNFCItem, SellerOTPItem,
)
from sqlalchemy import select as _sa_select
from shared.services.guarantee_policy_service import is_guarantee_active
from shared.services.nocodb_service import NocoDBService

logger = logging.getLogger(__name__)
router = Router()

CC_PHOTO = resolve_bot_photo("cc", fallback_path="media/Fullz.jpg")


@router.message(F.text.func(lambda value: ButtonTexts.matches("CC", value)))
async def cc_main_handler(message: Message, session: AsyncSession, texts, buttons):
    """Главное меню CC — категории из CCCategory или дефолтные"""
    from shared.cc_catalog import get_cc_categories
    categories = await get_cc_categories(session)
    counts = await MenuCountService.get_cc_counts(session)
    kb = cc_main_keyboard(buttons, categories, counts["by_category"])
    try:
        if CC_PHOTO:
            await message.answer_photo(
                photo=CC_PHOTO,
                caption=texts.CC_MAIN if hasattr(texts, "CC_MAIN") else "💳 **CC**\n\nSelect category:",
                reply_markup=kb,
                parse_mode="Markdown"
            )
        else:
            raise RuntimeError("CC photo is not configured")
    except Exception as e:
        logger.exception(e)
        await message.answer("💳 CC\n\nSelect category:", reply_markup=kb)


@router.callback_query(F.data == "cc_main")
async def cc_main_callback(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    """Возврат в главное меню CC"""
    from shared.cc_catalog import get_cc_categories
    categories = await get_cc_categories(session)
    counts = await MenuCountService.get_cc_counts(session)
    kb = cc_main_keyboard(buttons, categories, counts["by_category"])
    try:
        await callback.message.delete()
        if CC_PHOTO:
            await callback.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=CC_PHOTO,
                caption=texts.CC_MAIN if hasattr(texts, "CC_MAIN") else "💳 CC\n\nSelect category:",
                reply_markup=kb,
                parse_mode="Markdown"
            )
        else:
            raise RuntimeError("CC photo is not configured")
    except Exception:
        await safe_edit_message(
            callback,
            texts.CC_MAIN if hasattr(texts, "CC_MAIN") else "💳 CC\n\nSelect category:",
            reply_markup=kb,
            parse_mode="Markdown"
        )
    await callback.answer()


async def _cc_render_list(
    callback: CallbackQuery,
    session: AsyncSession,
    buttons,
    category_code: str,
    page: int = 0,
    sort_key: str = "price_asc",
    bin_filter: str | None = None,
    zip_filter: str | None = None,
):
    from shared.cc_catalog import get_cc_items_for_category
    items = await get_cc_items_for_category(
        session,
        category_code,
        bin_prefix=bin_filter,
        zip_q=zip_filter,
        sort_price="desc" if sort_key == "price_desc" else "asc",
    )
    if not items:
        await safe_edit_message(
            callback,
            f"📂 Category: {category_code}\n\nNo items in this category yet.",
            reply_markup=cc_empty_category_keyboard(buttons),
            parse_mode="Markdown",
        )
        return
    extra = ""
    if bin_filter:
        extra += f"\n🔍 BIN: `{bin_filter}`"
    if zip_filter:
        extra += f"\n🔍 ZIP: `{zip_filter}`"
    await safe_edit_message(
        callback,
        f"📂 Category: {category_code}{extra}\n\nSelect item:",
        reply_markup=cc_catalog_keyboard(
            buttons, items, category_code, page=page, sort_key=sort_key,
            bin_filter=bin_filter, zip_filter=zip_filter,
        ),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("cc_cat:"))
async def cc_category_handler(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    """Каталог товаров в категории CC — CCItem + SellerCCItem (approved)"""
    category_code = callback.data.split(":")[1]
    await _cc_render_list(callback, session, buttons, category_code, page=0, sort_key="price_asc")
    await callback.answer()


@router.callback_query(F.data.startswith("cc_listpg:"))
async def cc_list_page_handler(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    parts = callback.data.split(":")
    # cc_listpg:usa:0:price_asc:-:- 
    category_code = parts[1]
    page = int(parts[2])
    sort_key = parts[3]
    bin_f = None if len(parts) < 5 or parts[4] in ("", "-") else parts[4]
    zip_f = None if len(parts) < 6 or parts[5] in ("", "-") else parts[5]
    await _cc_render_list(
        callback, session, buttons, category_code, page=page, sort_key=sort_key,
        bin_filter=bin_f, zip_filter=zip_f,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cc_ask_bin:"))
async def cc_ask_bin(callback: CallbackQuery, state: FSMContext, buttons):
    parts = callback.data.split(":")
    category_code = parts[1]
    sort_key = parts[2] if len(parts) > 2 else "price_asc"
    zip_f = None if len(parts) < 4 or parts[3] in ("", "-") else parts[3]
    await state.set_state(CCFilterStates.waiting_bin)
    await state.update_data(cc_cat=category_code, cc_sort=sort_key, cc_zip=zip_f)
    await callback.message.edit_text(
        f"🔍 Send **6-digit BIN** for category `{category_code}` (or /cancel):",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=buttons.CANCEL, callback_data=f"cc_cat:{category_code}")],
        ]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cc_ask_zip:"))
async def cc_ask_zip(callback: CallbackQuery, state: FSMContext, buttons):
    parts = callback.data.split(":")
    category_code = parts[1]
    sort_key = parts[2] if len(parts) > 2 else "price_asc"
    bin_f = None if len(parts) < 4 or parts[3] in ("", "-") else parts[3]
    await state.set_state(CCFilterStates.waiting_zip)
    await state.update_data(cc_cat=category_code, cc_sort=sort_key, cc_bin=bin_f)
    await callback.message.edit_text(
        f"🔍 Send **ZIP** to filter (category `{category_code}`) or /cancel:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=buttons.CANCEL, callback_data=f"cc_cat:{category_code}")],
        ]),
    )
    await callback.answer()


@router.message(CCFilterStates.waiting_bin, F.text)
async def cc_receive_bin(message: Message, state: FSMContext, session: AsyncSession, buttons):
    data = await state.get_data()
    await state.clear()
    raw = (message.text or "").strip().replace(" ", "")
    if len(raw) < 6:
        await message.answer("BIN must be at least 6 digits.")
        return
    bin_f = raw[:6]
    cat = data.get("cc_cat", "usa")
    sort_key = data.get("cc_sort", "price_asc")
    zip_f = data.get("cc_zip")
    from shared.cc_catalog import get_cc_items_for_category
    items = await get_cc_items_for_category(
        session, cat, bin_prefix=bin_f, zip_q=zip_f, sort_price="desc" if sort_key == "price_desc" else "asc",
    )
    if not items:
        await message.answer(f"No items for BIN `{bin_f}`.", reply_markup=cc_empty_category_keyboard(buttons))
        return
    extra = f"\n🔍 BIN: `{bin_f}`"
    if zip_f:
        extra += f"\n🔍 ZIP: `{zip_f}`"
    await message.answer(
        f"📂 Category: {cat}{extra}\n\nSelect item:",
        reply_markup=cc_catalog_keyboard(buttons, items, cat, page=0, sort_key=sort_key, bin_filter=bin_f, zip_filter=zip_f),
        parse_mode="Markdown",
    )


@router.message(CCFilterStates.waiting_zip, F.text)
async def cc_receive_zip(message: Message, state: FSMContext, session: AsyncSession, buttons):
    data = await state.get_data()
    await state.clear()
    zip_f = (message.text or "").strip()
    if len(zip_f) < 3:
        await message.answer("ZIP too short.")
        return
    cat = data.get("cc_cat", "usa")
    sort_key = data.get("cc_sort", "price_asc")
    bin_f = data.get("cc_bin")
    from shared.cc_catalog import get_cc_items_for_category
    items = await get_cc_items_for_category(
        session, cat, bin_prefix=bin_f, zip_q=zip_f, sort_price="desc" if sort_key == "price_desc" else "asc",
    )
    if not items:
        await message.answer(f"No items for ZIP `{zip_f}`.", reply_markup=cc_empty_category_keyboard(buttons))
        return
    extra = f"\n🔍 ZIP: `{zip_f}`"
    if bin_f:
        extra = f"\n🔍 BIN: `{bin_f}`" + extra
    await message.answer(
        f"📂 Category: {cat}{extra}\n\nSelect item:",
        reply_markup=cc_catalog_keyboard(buttons, items, cat, page=0, sort_key=sort_key, bin_filter=bin_f, zip_filter=zip_f),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("cc_item:"))
async def cc_item_detail(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    parts = callback.data.split(":")
    category_code = parts[1]
    item_id = parts[2]
    bin_f = None if len(parts) < 4 or parts[3] in ("", "-") else parts[3]
    zip_f = None if len(parts) < 5 or parts[4] in ("", "-") else parts[4]
    item = None
    if item_id.isdigit():
        si = await session.scalar(select(SellerCCItem).where(SellerCCItem.id == int(item_id)))
        if si:
            from shared.utils.seller_card_renderers import render_cc_description
            item = {
                "id": str(si.id),
                "name": si.item_name,
                "price": float(si.buyer_price),
                "source": "seller",
                "seller_item_id": si.id,
                "description": render_cc_description(si),
            }
    else:
        from shared.database.models import CCItem
        ci = await session.scalar(select(CCItem).where(CCItem.cc_code == item_id))
        if ci:
            item = {
                "id": ci.cc_code,
                "name": ci.name,
                "price": float(ci.price),
                "source": "admin",
                "description": ci.description or "",
            }
    if not item:
        await callback.answer("Item not found", show_alert=True)
        return
    text = f"💳 **{item['name']}**\n\nPrice: ${item['price']}\n\n{item.get('description', '')}"
    bf, zf = bin_f or "-", zip_f or "-"
    back_cb = f"cc_listpg:{category_code}:0:price_asc:{bf}:{zf}"
    await safe_edit_message(
        callback,
        text,
        reply_markup=cc_item_detail_keyboard(buttons, item, category_code, back_callback=back_cb),
        parse_mode="Markdown"
    )
    await callback.answer()


def _build_cc_payload_text(item: SellerCCItem) -> str:
    """Deliver card to buyer in world-format:
    NUMBER|EXP|CVV|TYPE|BRAND|LVL|BANK|COUNTRY|HOLDER|ADDR|STATE|CITY|ZIP|Info|REF
    """
    ex = item.extra_data or {}
    number  = item.number or ""
    exp_mm  = int(item.exp_mm or 0)
    exp_yy  = str(item.exp_yyyy or "")[-2:] if item.exp_yyyy else ""
    exp     = ex.get("exp") or (f"{exp_mm:02d}/{exp_yy}" if exp_mm else "")
    cvv     = item.cvv or ""
    c_type  = ex.get("card_type") or ""
    brand   = item.card_brand or ex.get("brand") or ""
    level   = item.card_level or ex.get("level") or ""
    bank    = item.bank_name or ex.get("bank") or ""
    country = item.country or ex.get("country") or ""
    holder  = ex.get("holder") or " ".join(p for p in [item.fname, item.lname] if p)
    address = item.address or ex.get("address") or ""
    state   = item.state or ex.get("state") or ""
    city    = item.city or ex.get("city") or ""
    zip_c   = item.zip or ex.get("zip") or ""
    info    = ex.get("info") or ""
    ref     = ex.get("ref") or ""
    return "|".join([
        number, exp, cvv,
        c_type, brand, level, bank, country,
        holder, address, state, city, zip_c,
        info, ref,
    ])


@router.callback_query(F.data.startswith("cc_buy:"))
async def cc_buy(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, buttons):
    _, seller_item_id, category_code = callback.data.split(":")
    item = await session.scalar(select(SellerCCItem).where(SellerCCItem.id == int(seller_item_id)))
    if not item or item.moderation_status != "approved" or not item.is_active or not item.is_in_stock:
        await callback.answer("Item is unavailable", show_alert=True)
        return
    text = (
        f"⚠️ Confirm purchase?\n\n"
        f"💳 {item.item_name}\n"
        f"💵 ${float(item.buyer_price):.2f} will be deducted from your balance."
    )
    await state.update_data(
        checkout_category="cc",
        checkout_service_name=item.product_subtype,
        checkout_base_price=str(item.buyer_price),
        checkout_confirm_text=text,
        checkout_keyboard_type="custom",
        checkout_confirm_callback=f"cc_buy_confirm:{item.id}",
        checkout_cancel_callback=f"cc_cat:{category_code}",
        checkout_parse_mode=None,
        selected_coupon_code=None,
        selected_user_coupon_id=None,
        cc_checkout_item_id=item.id,
        cc_checkout_category_code=category_code,
    )
    await state.set_state(OrderStates.confirmation)
    await safe_edit_message(
        callback,
        text,
        reply_markup=cc_buy_confirm_keyboard(buttons, item.id, category_code),
        parse_mode=None,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cc_buy_confirm:"))
async def cc_buy_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, buttons):
    item_id = int(callback.data.split(":")[1])
    item = await session.scalar(select(SellerCCItem).where(SellerCCItem.id == item_id))
    if not item or item.moderation_status != "approved" or not item.is_active or not item.is_in_stock:
        await callback.answer("Item is unavailable", show_alert=True)
        return
    state_data = await state.get_data()
    pricing = await CheckoutCouponService.get_checkout_pricing(
        session,
        telegram_user_id=callback.from_user.id,
        state_data={
            "checkout_category": "cc",
            "checkout_service_name": item.product_subtype,
            "checkout_base_price": str(item.buyer_price),
            "selected_coupon_code": state_data.get("selected_coupon_code"),
        },
    )
    charged = await OrderService.charge_balance(
        session,
        callback.from_user.id,
        pricing.final_amount,
        description=f"CC purchase #{item.id}",
        commit=False,
    )
    if not charged:
        await callback.answer("Insufficient balance", show_alert=True)
        return

    item.is_in_stock = False
    item.stock_count = max(0, int(item.stock_count or 1) - 1)
    now = datetime.now(timezone.utc)
    CC_CHECK_WINDOW = 15
    order = SellerCCOrder(
        seller_id=item.seller_id,
        seller_cc_item_id=item.id,
        buyer_user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
        status="completed",
        product_type="cc",
        product_subtype=item.product_subtype,
        price_for_buyer=pricing.final_amount,
        price_for_seller=item.base_price or item.seller_price,
        quantity=1,
        result_data={"text": _build_cc_payload_text(item)},
        check_window_minutes=CC_CHECK_WINDOW,
        completed_at=now,
        auto_complete_at=now + timedelta(hours=24),
    )
    session.add(order)
    await session.commit()
    await state.clear()
    if pricing.applied:
        NocoDBService.log_event(
            event_type="coupon_applied",
            actor_type="buyer",
            actor_id=callback.from_user.id,
            target_type="seller_cc_order",
            target_id=order.id,
            status="applied",
            payload={
                "coupon_code": pricing.code,
                "category": "cc",
                "service_name": item.product_subtype,
                "original_amount": float(pricing.original_amount),
                "discount_amount": float(pricing.discount_amount),
                "final_amount": float(pricing.final_amount),
            },
            timestamp=now,
        )
    open_text = getattr(buttons, "OPEN_PRODUCT", "📦 Open Product")
    reveal_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=open_text, callback_data=f"cc_reveal:{order.id}")],
        [InlineKeyboardButton(text=buttons.BACK, callback_data="back_main")],
    ])
    await safe_edit_message(
        callback,
        f"✅ *Purchase successful\\!*\n\n"
        f"💳 {item.item_name}\n\n"
        f"⚠️ *Press the button below to open your product\\.*\n"
        f"You will have *{CC_CHECK_WINDOW} minutes* to verify\\.\n"
        f"After that, payment is finalized to the seller\\.",
        reply_markup=reveal_kb,
        parse_mode="Markdown",
    )
    await callback.answer()


_CC_SPECIALS_MAP = {
    "cc_selfreg_cc": ("selfreg_cc", SellerSelfregCCItem, "🏧 Selfreg CC"),
    "cc_enroll":     ("enroll",     SellerEnrollItem,    "🏦 Enroll"),
    "cc_otp":        ("otp",        SellerOTPItem,       "🔑 OTP"),
    "cc_nfc":        ("nfc",        SellerNFCItem,       "📱 NFC"),
}


def _cc_specials_item_text(item, kind: str) -> str:
    if kind == "selfreg_cc":
        return f"🏧 {getattr(item, 'bank_name', '')} | ${float(item.price):.2f}"
    if kind == "enroll":
        return f"🏦 {getattr(item, 'portal', '')} ${getattr(item, 'balance', 0):.0f} | ${float(item.price):.2f}"
    if kind == "otp":
        return f"🔑 {getattr(item, 'bank_name', '')} | ${float(item.price):.2f}"
    if kind == "nfc":
        return f"📱 {getattr(item, 'bank_name', '')} | ${float(item.price):.2f}"
    return f"${float(item.price):.2f}"


@router.callback_query(F.data.in_(list(_CC_SPECIALS_MAP.keys())))
async def cc_specials_handler(callback: CallbackQuery, session: AsyncSession, buttons):
    """Routes CC sub-categories that are seller specials (Selfreg CC, Enroll, OTP, NFC)."""
    kind, model, label = _CC_SPECIALS_MAP[callback.data]
    if kind == "selfreg_cc":
        callback.data = "seller_specials_list:selfreg_cc"
        from mirror_bot.handlers.seller_specials import seller_specials_list
        await seller_specials_list(callback, session)
        return
    items = list((await session.execute(
        _sa_select(model)
        .join(Seller)
        .where(
            model.is_active == True,
            model.is_in_stock == True,
            model.moderation_status == "approved",
            Seller.is_approved == True,
            Seller.is_active == True,
        )
        .limit(20)
    )).scalars().all())
    item_rows = [
        [InlineKeyboardButton(
            text=_cc_specials_item_text(item, kind),
            callback_data=f"seller_specials_detail:{kind}:{item.id}",
        )]
        for item in items
    ]
    if not item_rows:
        item_rows.append([InlineKeyboardButton(
            text=getattr(buttons, "CC_NO_ITEMS", "📭 No items available"),
            callback_data="cc_main",
        )])
    await safe_edit_message(
        callback,
        f"*{label}*\n\nSelect item:",
        reply_markup=cc_specials_keyboard(buttons, item_rows),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cc_feedback:"))
async def cc_feedback(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, buttons):
    _, order_id, feedback_status = callback.data.split(":")
    order = await session.scalar(select(SellerCCOrder).where(SellerCCOrder.id == int(order_id)))
    if not order or order.buyer_user_id != callback.from_user.id:
        await callback.answer("Order not found", show_alert=True)
        return
    order.feedback_status = feedback_status
    order.feedback_at = datetime.now(timezone.utc)
    seller = await session.scalar(select(Seller).where(Seller.id == order.seller_id))
    if seller:
        if feedback_status == "liked":
            seller.likes_count = int(seller.likes_count or 0) + 1
        elif feedback_status == "disliked":
            seller.dislikes_count = int(seller.dislikes_count or 0) + 1
    await session.commit()
    await safe_edit_message(
        callback,
        "Feedback saved.",
        reply_markup=cc_feedback_done_keyboard(buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cc_report:"))
async def cc_report(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, buttons):
    order_id = int(callback.data.split(":")[1])
    order = await session.scalar(select(SellerCCOrder).where(SellerCCOrder.id == order_id))
    if not order or order.buyer_user_id != callback.from_user.id:
        await callback.answer("Order not found", show_alert=True)
        return
    if not is_guarantee_active(order.check_expires_at):
        await callback.answer("Report window expired (15 min)", show_alert=True)
        return
    order.report_status = "moderation_requested"
    order.reported_at = datetime.now(timezone.utc)
    await session.commit()
    try:
        from shared.services.admin_notification_service import AdminNotificationService
        await AdminNotificationService.notify_new_dispute(
            order_type="cc",
            order_id=order.id,
            buyer_user_id=callback.from_user.id,
            seller_id=order.seller_id,
        )
    except Exception:
        pass
    await safe_edit_message(
        callback,
        (
            "✅ Report submitted to moderation.\n\n"
            "📸 Attach your screenshot in a reply to support.\n"
            "You will receive a notification when a decision is made.\n\n"
            "No seller chat is available for CC orders."
        ),
        reply_markup=cc_report_done_keyboard(buttons),
    )
    await callback.answer()


CC_REVEAL_CHECK_WINDOW = 15


@router.callback_query(F.data.startswith("cc_reveal:"))
async def cc_reveal_handler(callback: CallbackQuery, session: AsyncSession, buttons):
    """Buyer presses 'Open Product' — starts the 15-minute guarantee timer and shows CC data."""
    order_id = int(callback.data.split(":")[1])
    order = await session.scalar(select(SellerCCOrder).where(SellerCCOrder.id == order_id))
    if not order or order.buyer_user_id != callback.from_user.id:
        await callback.answer("Order not found", show_alert=True)
        return

    now = datetime.now(timezone.utc)
    if not order.check_started_at:
        order.check_started_at = now
        order.check_expires_at = now + timedelta(minutes=CC_REVEAL_CHECK_WINDOW)
        order.auto_complete_at = order.check_expires_at
        await session.commit()

    cc_text = (order.result_data or {}).get("text", "No data")

    await safe_edit_message(
        callback,
        f"🔐 *CC Order #{order.id}*\n\n"
        f"⏱ *You have {CC_REVEAL_CHECK_WINDOW} minutes to verify\\.*\n"
        f"After that, payment goes to the seller\\.\n\n"
        f"🔑 *Your product:*\n`{cc_text}`\n\n"
        f"📸 Refund requires screenshot proof\\.\n"
        f"No seller chat available — moderation only\\.",
        reply_markup=cc_result_keyboard(buttons, order.id),
        parse_mode="Markdown",
    )
    await callback.answer()
