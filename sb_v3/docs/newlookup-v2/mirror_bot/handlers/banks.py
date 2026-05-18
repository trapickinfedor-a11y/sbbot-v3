from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from shared.database.models import Seller, SellerLogsItem
from mirror_bot.constants.bank_data import BankData
from mirror_bot.services.order_service import OrderService
from mirror_bot.services.checkout_coupon_service import CheckoutCouponService
from mirror_bot.services.user_service import UserService
from mirror_bot.utils.product_translations import ProductTranslations
from mirror_bot.constants.buttons_en import ButtonTexts
from mirror_bot.utils.message_utils import safe_edit_message
from mirror_bot.constants.prices import BulkDiscounts
from mirror_bot.constants.service_eta import ServiceETA
from mirror_bot.services.eta_service import ETAService
from mirror_bot.services.menu_counts_service import MenuCountService
from mirror_bot.utils.media_library import resolve_bot_photo
from mirror_bot.states.banks import BankStates
from mirror_bot.utils.catalog_pagination import clamp_page

logger = logging.getLogger(__name__)
router = Router()

BANK_AVAILABLE_CHECK_WINDOW = 60  # minutes — guarantee window for Available (seller stock) orders


# ============================================
# KEYBOARDS
# ============================================

def banks_main_keyboard(buttons, counts: dict | None = None) -> InlineKeyboardMarkup:
    counts = counts or {}
    brute_text = getattr(buttons, "BRUTE_BANK", None) or getattr(buttons, "BRUTE_BANK_SOON", "🔓 Brute BANK")
    logs_text = getattr(buttons, "BANKS_LOGS", "📋 Logs BA")
    merchant_text = getattr(buttons, "BANKS_MERCHANT", "🏪 Merchant")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ButtonTexts.with_count(buttons.BANKS_PERSONAL_VCC, counts.get("vcc")), callback_data="banks_vcc")],
        [InlineKeyboardButton(text=ButtonTexts.with_count(buttons.BANKS_PERSONAL, counts.get("personal")), callback_data="banks_personal")],
        [InlineKeyboardButton(text=ButtonTexts.with_count(buttons.BANKS_BUSINESS, counts.get("business")), callback_data="banks_business")],
        [InlineKeyboardButton(text=ButtonTexts.with_count(buttons.BANKS_CRYPTO, counts.get("crypto")), callback_data="banks_crypto")],
        [InlineKeyboardButton(text=ButtonTexts.with_count(merchant_text, counts.get("merchant")), callback_data="banks_merchant")],
        [InlineKeyboardButton(text=ButtonTexts.with_count(brute_text, counts.get("brute")), callback_data="banks_brute")],
        [InlineKeyboardButton(text=ButtonTexts.with_count(logs_text, counts.get("logs")), callback_data="banks_logs")],
        [InlineKeyboardButton(text=buttons.BACK, callback_data="back_main")],
    ])


def banks_section_keyboard(category: str, counts: dict, buttons_obj=None) -> InlineKeyboardMarkup:
    back_text = buttons_obj.BACK_TO_CATEGORIES if buttons_obj else "🏠 Back to Categories"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📦 Available [{counts.get('available', 0)}]", callback_data=f"banks_section:{category}:available")],
        [InlineKeyboardButton(text=f"📝 Per Order [{counts.get('per_order', 0)}]", callback_data=f"banks_section:{category}:order")],
        [InlineKeyboardButton(text=back_text, callback_data="banks_main")],
    ])


BANK_SUBS_PER_PAGE = 15
BANK_ITEMS_PER_PAGE = 10


def _sort_price_items(items: list, sort_key: str) -> list:
    rev = sort_key == "price_desc"
    return sorted(items, key=lambda x: float(x.get("price", 0) or 0), reverse=rev)


def banks_bank_names_keyboard(
    category: str,
    section: str,
    bank_rows: list,
    page: int = 0,
    buttons_obj=None,
) -> InlineKeyboardMarkup:
    """Subcategories by bank_name with counts."""
    total_pages = max(1, (len(bank_rows) + BANK_SUBS_PER_PAGE - 1) // BANK_SUBS_PER_PAGE)
    page = clamp_page(page, len(bank_rows), BANK_SUBS_PER_PAGE)
    start = page * BANK_SUBS_PER_PAGE
    chunk = bank_rows[start : start + BANK_SUBS_PER_PAGE]
    rows = []
    for i, row in enumerate(chunk):
        global_idx = start + i
        label = row["bank_name"][:28] + ("…" if len(row["bank_name"]) > 28 else "")
        rows.append([
            InlineKeyboardButton(
                text=f"{label} [{row['available_count']}]",
                callback_data=f"banks_pick:{category}:{section}:{global_idx}",
            )
        ])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"banks_bnpage:{category}:{section}:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="page_info"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"banks_bnpage:{category}:{section}:{page + 1}"))
    if nav:
        rows.append(nav)
    back_text = buttons_obj.BACK_TO_CATEGORIES if buttons_obj else "🏠 Back to Categories"
    rows.append([InlineKeyboardButton(text=back_text, callback_data=f"banks_{category}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def banks_catalog_keyboard(
    category: str,
    section: str,
    items: list,
    page: int = 0,
    items_per_page: int = 5,
    buttons_obj=None,
    *,
    sort_key: str = "price_asc",
    bank_idx: int | None = None,
) -> InlineKeyboardMarkup:
    items = _sort_price_items(items, sort_key)
    total_pages = max(1, (len(items) + items_per_page - 1) // items_per_page)
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(items))
    rows = []
    for item in items[start_idx:end_idx]:
        if section == "available":
            extra = f" [{item.get('available_count', 0)}]"
        else:
            extra = " [∞]"
        rows.append([InlineKeyboardButton(
            text=f"{item['name']} | ${item['price']}{extra}",
            callback_data=f"bank_item:{section}:{item['id']}",
        )])
    nav = []
    if page > 0:
        prev_text = buttons_obj.PREV_PAGE if buttons_obj else "⬅️ Prev"
        if section == "available" and bank_idx is not None:
            nav.append(InlineKeyboardButton(
                text=prev_text,
                callback_data=f"banks_pick_page:{category}:{section}:{bank_idx}:{page - 1}:{sort_key}",
            ))
        else:
            nav.append(InlineKeyboardButton(text=prev_text, callback_data=f"banks_page:{category}:{section}:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="page_info"))
    if page < total_pages - 1:
        next_text = buttons_obj.NEXT_PAGE if buttons_obj else "Next ➡️"
        if section == "available" and bank_idx is not None:
            nav.append(InlineKeyboardButton(
                text=next_text,
                callback_data=f"banks_pick_page:{category}:{section}:{bank_idx}:{page + 1}:{sort_key}",
            ))
        else:
            nav.append(InlineKeyboardButton(text=next_text, callback_data=f"banks_page:{category}:{section}:{page + 1}"))
    if nav:
        rows.append(nav)
    if section == "available" and bank_idx is not None:
        sort_next = "price_desc" if sort_key == "price_asc" else "price_asc"
        sort_label = "💲 Price ↑" if sort_key == "price_asc" else "💲 Price ↓"
        rows.append([
            InlineKeyboardButton(
                text=sort_label,
                callback_data=f"banks_sort:{category}:{section}:{bank_idx}:{sort_next}",
            )
        ])
    if section == "available" and bank_idx is not None:
        rows.append([InlineKeyboardButton(text="⬅️ Banks list", callback_data=f"banks_section:{category}:{section}")])
    else:
        back_text = buttons_obj.BACK_TO_CATEGORIES if buttons_obj else "🏠 Back to Categories"
        rows.append([InlineKeyboardButton(text=back_text, callback_data=f"banks_{category}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def bank_item_keyboard(bank_id: str, section: str, buttons, is_in_stock: bool = True) -> InlineKeyboardMarkup:
    """Quantity selection keyboard.
    Per-Order → bank_qty (worker fulfillment)
    In Stock  → bank_buy (seller stock)
    On Name   → bank_on_name (worker, buyer provides name/SSN)
    """
    order_by_name_text = getattr(buttons, "ORDER_BY_NAME", "📝 Order by Name")
    if not is_in_stock:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Per Order", callback_data=f"bank_qty:{section}:{bank_id}:1")],
            [InlineKeyboardButton(text=order_by_name_text, callback_data=f"bank_on_name:{section}:{bank_id}")],
            [InlineKeyboardButton(text=buttons.BACK_TO_LIST, callback_data=f"bank_back:{section}:{bank_id}")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=buttons.get_qty_button(2, 0), callback_data=f"bank_qty:{section}:{bank_id}:2"),
            InlineKeyboardButton(text=buttons.get_qty_button(3, BulkDiscounts.BANKS_QTY_3), callback_data=f"bank_qty:{section}:{bank_id}:3"),
            InlineKeyboardButton(text=buttons.get_qty_button(5, BulkDiscounts.BANKS_QTY_5), callback_data=f"bank_qty:{section}:{bank_id}:5"),
            InlineKeyboardButton(text=buttons.get_qty_button(10, BulkDiscounts.BANKS_QTY_10), callback_data=f"bank_qty:{section}:{bank_id}:10"),
        ],
        [InlineKeyboardButton(text=buttons.BANK_CUSTOM_QTY, callback_data=f"bank_custom:{section}:{bank_id}")],
        [InlineKeyboardButton(text=buttons.BUY_1_ITEM, callback_data=f"bank_buy:{section}:{bank_id}:1")],
        [InlineKeyboardButton(text=order_by_name_text, callback_data=f"bank_on_name:{section}:{bank_id}")],
        [InlineKeyboardButton(text=buttons.BACK_TO_LIST, callback_data=f"bank_back:{section}:{bank_id}")],
    ])


def _bank_reveal_keyboard(order_id: int, buttons) -> InlineKeyboardMarkup:
    """After purchase — buyer must press 'Open' to start the guarantee timer."""
    open_text = getattr(buttons, "OPEN_PRODUCT", "📦 Open Product")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=open_text, callback_data=f"bank_reveal:{order_id}")],
        [InlineKeyboardButton(text=buttons.BACK, callback_data="back_main")],
    ])


def _bank_revealed_keyboard(order_id: int, seller_bank_has_chat: bool = True) -> InlineKeyboardMarkup:
    """After reveal — buyer sees Ask Seller / Report / Rate."""
    rows = []
    if seller_bank_has_chat:
        rows.append([InlineKeyboardButton(text="💬 Ask Seller", callback_data=f"bank_ask_seller:{order_id}")])
    rows += [
        [InlineKeyboardButton(text="⚠️ Report Issue", callback_data=f"bank_report:{order_id}")],
        [
            InlineKeyboardButton(text="👍 Like", callback_data=f"bank_feedback:{order_id}:liked"),
            InlineKeyboardButton(text="👎 Dislike", callback_data=f"bank_feedback:{order_id}:disliked"),
        ],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _parse_bank_section_callback(callback_data: str, prefix: str):
    parts = callback_data.split(":")
    if len(parts) == 4 and parts[0] == prefix:
        _, section, bank_id, value = parts
        return section, bank_id, value
    if len(parts) == 3 and parts[0] == prefix:
        _, bank_id, value = parts
        return "order", bank_id, value
    return None, None, None


def _parse_bank_callback_with_section(callback_data: str, prefix: str):
    parts = callback_data.split(":")
    if len(parts) == 3 and parts[0] == prefix:
        _, section, bank_id = parts
        return section, bank_id
    if len(parts) == 2 and parts[0] == prefix:
        _, bank_id = parts
        return "order", bank_id
    return None, None


@router.message(F.text.func(lambda value: ButtonTexts.matches("BANKS", value)))
async def banks_main_handler(message: Message, session: AsyncSession, texts, buttons):
    counts = await MenuCountService.get_banks_counts(session)
    banks_photo = resolve_bot_photo("banks", fallback_path="media/banks.jpg")
    try:
        if banks_photo:
            await message.answer_photo(
                photo=banks_photo,
                caption=f"{buttons.BANKS}\n\n{texts.BANKS_MAIN}",
                reply_markup=banks_main_keyboard(
                    buttons,
                    {
                        **counts["by_category"],
                        "brute": counts["brute"],
                    },
                )
            )
        else:
            raise RuntimeError("Banks photo is not configured")
    except Exception:
        await message.answer(
            texts.BANKS_MAIN,
            reply_markup=banks_main_keyboard(
                buttons,
                {
                    **counts["by_category"],
                    "brute": counts["brute"],
                },
            )
        )


@router.callback_query(F.data == "banks_main")
async def banks_main_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession, texts, buttons):
    await state.clear()
    counts = await MenuCountService.get_banks_counts(session)
    banks_photo = resolve_bot_photo("banks", fallback_path="media/banks.jpg")
    # Для возврата в banks всегда отправляем с фото
    try:
        await callback.message.delete()
        if banks_photo:
            await callback.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=banks_photo,
                caption=texts.BANKS_MAIN,
                reply_markup=banks_main_keyboard(
                    buttons,
                    {
                        **counts["by_category"],
                        "brute": counts["brute"],
                    },
                )
            )
        else:
            raise RuntimeError("Banks photo is not configured")
    except Exception:
        # Fallback без фото
        await safe_edit_message(
            callback,
            texts.BANKS_MAIN,
            reply_markup=banks_main_keyboard(
                buttons,
                {
                    **counts["by_category"],
                    "brute": counts["brute"],
                },
            )
        )
    await callback.answer()


_BANKS_SPECIALS_MAP = {
    "banks_logs": "logs",
}


@router.callback_query(F.data.in_(list(_BANKS_SPECIALS_MAP.keys())))
async def banks_specials_handler(callback: CallbackQuery, session: AsyncSession):
    """Routes BANKS sub-categories that are seller specials."""
    kind = _BANKS_SPECIALS_MAP[callback.data]
    await _show_specials_in_banks(callback, session, kind)


@router.callback_query(F.data == "banks_merchant")
async def banks_merchant_handler(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    """Merchant — available stock with bank_name subcategories."""
    category_name = BankData.CATEGORIES["merchant"]["name"]
    bank_rows = await BankData.get_available_bank_names(session, "merchant")

    if not bank_rows:
        await safe_edit_message(
            callback,
            f"{texts.BANKS_SELECT_ITEM.format(category_name=category_name)}\n\n❌ No items in stock.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=buttons.BACK, callback_data="banks_main")],
            ]),
        )
        await callback.answer()
        return

    await safe_edit_message(
        callback,
        texts.BANKS_SELECT_ITEM.format(category_name=category_name) + "\n\nSelect bank:",
        reply_markup=banks_bank_names_keyboard("merchant", "available", bank_rows, page=0, buttons_obj=buttons),
    )
    await callback.answer()


async def _show_specials_in_banks(callback: CallbackQuery, session: AsyncSession, kind: str):
    """Show a seller specials catalog scoped to the BANKS section (back → banks_main)."""
    items = list((await session.execute(
        select(SellerLogsItem if kind == "logs" else _specials_model(kind))
        .join(Seller)
        .where(
            _specials_model(kind).is_active == True,
            _specials_model(kind).is_in_stock == True,
            _specials_model(kind).moderation_status == "approved",
            Seller.is_approved == True,
            Seller.is_active == True,
        )
        .limit(20)
    )).scalars().all())
    label = {
        "logs": "📋 Logs BA", "selfreg_ba": "🏧 Selfreg BA",
        "enroll": "🏦 Enroll", "nfc": "📱 NFC", "otp": "🔑 OTP",
    }.get(kind, kind.title())
    rows = [
        [InlineKeyboardButton(
            text=_specials_item_text(item, kind),
            callback_data=f"seller_specials_detail:{kind}:{item.id}",
        )]
        for item in items
    ]
    if not rows:
        rows.append([InlineKeyboardButton(text="No items available", callback_data="banks_main")])
    rows.append([InlineKeyboardButton(text="🏠 Back to Banks", callback_data="banks_main")])
    await safe_edit_message(
        callback, f"*{label}*\n\nSelect item:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="Markdown",
    )
    await callback.answer()


def _specials_model(kind: str):
    from shared.database.models import (
        SellerLogsItem, SellerBankItem, SellerEnrollItem,
        SellerNFCItem, SellerOTPItem,
    )
    return {
        "logs": SellerLogsItem,
        "selfreg_ba": SellerBankItem,
        "enroll": SellerEnrollItem,
        "nfc": SellerNFCItem,
        "otp": SellerOTPItem,
    }[kind]


def _specials_item_text(item, kind: str) -> str:
    if kind == "logs":
        return f"📋 {item.bank} ${item.total_balance:.0f} | ${float(item.price):.2f}"
    if kind == "selfreg_ba":
        return f"🏧 {getattr(item, 'bank', '')} {getattr(item, 'state', '')} | ${float(item.price):.2f}"
    if kind == "enroll":
        return f"🏦 {getattr(item, 'portal', '')} ${getattr(item, 'balance', 0):.0f} | ${float(item.price):.2f}"
    if kind == "nfc":
        return f"📱 {getattr(item, 'bank', '')} | ${float(item.price):.2f}"
    if kind == "otp":
        return f"🔑 {getattr(item, 'service', '')} | ${float(item.price):.2f}"
    return f"${float(item.price):.2f}"




@router.callback_query(F.data.in_(["banks_vcc", "banks_personal", "banks_business", "banks_crypto"]))
async def banks_category_handler(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    category = callback.data.replace("banks_", "")
    category_name = BankData.CATEGORIES[category]["name"]
    counts = await MenuCountService.get_bank_section_counts(session, category)
    await safe_edit_message(
        callback,
        texts.BANKS_SELECT_ITEM.format(category_name=category_name),
        reply_markup=banks_section_keyboard(category, counts, buttons_obj=buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("banks_section:"))
async def banks_section_handler(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    _, category, section = callback.data.split(":")
    category_name = BankData.CATEGORIES[category]["name"]
    if section == "available":
        bank_rows = await BankData.get_available_bank_names(session, category)
        if not bank_rows:
            await safe_edit_message(
                callback,
                f"{texts.BANKS_SELECT_ITEM.format(category_name=category_name)}\n\n❌ No items in this section.",
                reply_markup=banks_section_keyboard(
                    category,
                    await MenuCountService.get_bank_section_counts(session, category),
                    buttons_obj=buttons,
                ),
            )
            await callback.answer()
            return
        await safe_edit_message(
            callback,
            texts.BANKS_SELECT_ITEM.format(category_name=category_name) + "\n\nSelect bank:",
            reply_markup=banks_bank_names_keyboard(category, section, bank_rows, page=0, buttons_obj=buttons),
        )
        await callback.answer()
        return

    items = await BankData.get_per_order_items_by_category(session, category)
    if not items:
        await safe_edit_message(
            callback,
            f"{texts.BANKS_SELECT_ITEM.format(category_name=category_name)}\n\n❌ No items in this section.",
            reply_markup=banks_section_keyboard(
                category,
                await MenuCountService.get_bank_section_counts(session, category),
                buttons_obj=buttons,
            ),
        )
        await callback.answer()
        return

    await safe_edit_message(
        callback,
        texts.BANKS_SELECT_ITEM.format(category_name=category_name),
        reply_markup=banks_catalog_keyboard(
            category, section, items, page=0, items_per_page=BANK_ITEMS_PER_PAGE, buttons_obj=buttons
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("banks_bnpage:"))
async def banks_bnpage_handler(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    _, category, section, page_str = callback.data.split(":")
    page = int(page_str)
    bank_rows = await BankData.get_available_bank_names(session, category)
    category_name = BankData.CATEGORIES[category]["name"]
    await safe_edit_message(
        callback,
        texts.BANKS_SELECT_ITEM.format(category_name=category_name) + "\n\nSelect bank:",
        reply_markup=banks_bank_names_keyboard(category, section, bank_rows, page=page, buttons_obj=buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("banks_pick:"))
async def banks_pick_handler(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    _, category, section, idx_str = callback.data.split(":")
    bank_rows = await BankData.get_available_bank_names(session, category)
    idx = int(idx_str)
    if idx < 0 or idx >= len(bank_rows):
        await callback.answer("Invalid selection", show_alert=True)
        return
    bank_name = bank_rows[idx]["bank_name"]
    items = await BankData.get_available_items_by_bank_name(session, category, bank_name)
    category_name = BankData.CATEGORIES[category]["name"]
    if not items:
        await safe_edit_message(
            callback,
            f"{texts.BANKS_SELECT_ITEM.format(category_name=category_name)}\n\n❌ No listings for this bank.",
            reply_markup=banks_bank_names_keyboard(category, section, bank_rows, page=0, buttons_obj=buttons),
        )
        await callback.answer()
        return
    await safe_edit_message(
        callback,
        texts.BANKS_SELECT_ITEM.format(category_name=category_name) + f"\n\n🏦 {bank_name}",
        reply_markup=banks_catalog_keyboard(
            category,
            section,
            items,
            page=0,
            items_per_page=BANK_ITEMS_PER_PAGE,
            buttons_obj=buttons,
            sort_key="price_asc",
            bank_idx=idx,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("banks_pick_page:"))
async def banks_pick_page_handler(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    _, category, section, idx_str, page_str, sort_key = callback.data.split(":")
    bank_rows = await BankData.get_available_bank_names(session, category)
    idx = int(idx_str)
    page = int(page_str)
    if idx < 0 or idx >= len(bank_rows):
        await callback.answer("Invalid selection", show_alert=True)
        return
    bank_name = bank_rows[idx]["bank_name"]
    items = await BankData.get_available_items_by_bank_name(session, category, bank_name)
    category_name = BankData.CATEGORIES[category]["name"]
    await safe_edit_message(
        callback,
        texts.BANKS_SELECT_ITEM.format(category_name=category_name) + f"\n\n🏦 {bank_name}",
        reply_markup=banks_catalog_keyboard(
            category,
            section,
            items,
            page=page,
            items_per_page=BANK_ITEMS_PER_PAGE,
            buttons_obj=buttons,
            sort_key=sort_key,
            bank_idx=idx,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("banks_sort:"))
async def banks_sort_handler(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    _, category, section, idx_str, sort_key = callback.data.split(":")
    bank_rows = await BankData.get_available_bank_names(session, category)
    idx = int(idx_str)
    if idx < 0 or idx >= len(bank_rows):
        await callback.answer("Invalid selection", show_alert=True)
        return
    bank_name = bank_rows[idx]["bank_name"]
    items = await BankData.get_available_items_by_bank_name(session, category, bank_name)
    category_name = BankData.CATEGORIES[category]["name"]
    await safe_edit_message(
        callback,
        texts.BANKS_SELECT_ITEM.format(category_name=category_name) + f"\n\n🏦 {bank_name}",
        reply_markup=banks_catalog_keyboard(
            category,
            section,
            items,
            page=0,
            items_per_page=BANK_ITEMS_PER_PAGE,
            buttons_obj=buttons,
            sort_key=sort_key,
            bank_idx=idx,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("banks_page:"))
async def banks_page_handler(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    _, category, section, page_str = callback.data.split(":")
    page = int(page_str)

    if section == "available":
        items = await BankData.get_available_items_by_category(session, category)
    else:
        items = await BankData.get_per_order_items_by_category(session, category)
    category_name = BankData.CATEGORIES[category]["name"]
    await safe_edit_message(
        callback,
        texts.BANKS_SELECT_ITEM.format(category_name=category_name),
        reply_markup=banks_catalog_keyboard(
            category, section, items, page=page, items_per_page=BANK_ITEMS_PER_PAGE, buttons_obj=buttons
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "bank_oos_alert")
async def bank_oos_alert(callback: CallbackQuery, texts, **kwargs):
    await callback.answer("❌ This bank is currently out of stock", show_alert=True)


@router.callback_query(F.data.startswith("bank_item:"))
async def bank_item_detail(callback: CallbackQuery, session: AsyncSession, texts, buttons, user_language: str):
    section, bank_id = _parse_bank_callback_with_section(callback.data, "bank_item")
    bank = await BankData.get_bank_by_id_async(session, bank_id, section=section)
    
    if not bank:
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return
    
    is_in_stock = section == "available"
    
    product_data = texts.PRODUCT_DATA.get(bank_id)
    if product_data:
        text = texts.PRODUCT_DESCRIPTION_TEMPLATE.format(
            product_name=bank['name'],
            category=product_data['category'],
            price=str(bank['price']),
            delivery=product_data['delivery'],
            description=product_data['description'],
            tutorial_link=product_data['tutorial']
        )
    else:
        text = texts.PRODUCT_DESCRIPTION_TEMPLATE.format(
            product_name=bank['name'],
            category=texts.PREMIUM_SERVICE,
            price=str(bank['price']),
            delivery="1-6 " + texts.HOURS,
            description=texts.PREMIUM_SERVICE,
            tutorial_link="#"
        )
    
    stock_label = "\n\n✅ *In Stock*" if is_in_stock else "\n\n❌ *Out of Stock*"
    text += stock_label
    
    await safe_edit_message(
        callback,
        text,
        reply_markup=bank_item_keyboard(bank_id, section, buttons, is_in_stock=is_in_stock),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bank_qty:"))
async def bank_quantity_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext, mirror_bot_id: int, texts, buttons):
    logger.info(f"[BANKS] Quantity handler called: {callback.data}")
    section, bank_id, qty_str = _parse_bank_section_callback(callback.data, "bank_qty")
    if not section:
        logger.error(f"Invalid callback data format: {callback.data}")
        await callback.answer(texts.ERROR_INVALID_DATA_FORMAT, show_alert=True)
        return
    quantity = int(qty_str)
    
    bank = await BankData.get_bank_by_id_async(session, bank_id, section=section)
    if not bank:
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return
    
    base_price = Decimal(str(bank['price'])) * Decimal(str(quantity))
    
    # Скидка за опт из prices.py
    discount_percent = BulkDiscounts.get_bank_discount(quantity)
    total_price = base_price * (Decimal('1') - Decimal(str(discount_percent)) / Decimal('100'))
    
    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)

    confirm_text = f"{texts.BULK_PURCHASE_TITLE}\n\n"
    confirm_text += f"{texts.BULK_PURCHASE_WARNING}\n\n"
    confirm_text += texts.BULK_PURCHASE_PRODUCT.format(product_name=bank['name']) + "\n"
    confirm_text += texts.BULK_PURCHASE_QUANTITY.format(quantity=quantity) + "\n"
    confirm_text += texts.BULK_PURCHASE_UNIT_PRICE.format(unit_price=bank['price']) + "\n"
    if discount_percent > 0:
        confirm_text += texts.BULK_PURCHASE_DISCOUNT.format(discount_percent=discount_percent) + "\n"
    confirm_text += texts.BULK_PURCHASE_TOTAL.format(total_price=total_price) + "\n\n"
    confirm_text += texts.BULK_PURCHASE_BALANCE.format(balance=user.balance if user else 0) + "\n"
    new_balance = (user.balance if user else Decimal("0")) - total_price
    confirm_text += texts.BULK_PURCHASE_NEW_BALANCE.format(new_balance=new_balance) + "\n\n"
    confirm_text += texts.BULK_PURCHASE_CONFIRM_TEXT.format(quantity=quantity, total_price=total_price)
    _bulk_eta = await ETAService.get_eta_text(session, "bank")
    confirm_text += f"\n\n⏱ *ETA:* {_bulk_eta}"

    await state.update_data(
        section=section,
        bank_id=bank_id,
        quantity=quantity,
        unit_price=float(bank['price']),
        total_price=float(total_price),
        discount_percent=discount_percent,
        checkout_category="banks",
        checkout_service_name=bank_id,
        checkout_base_price=str(total_price),
        checkout_confirm_text=confirm_text,
        checkout_keyboard_type="custom",
        checkout_confirm_callback="confirm_bulk_bank",
        checkout_cancel_callback="cancel_bulk_bank",
        checkout_parse_mode="Markdown",
        selected_coupon_code=None,
        selected_user_coupon_id=None,
    )
    await state.set_state(BankStates.confirm_bulk_purchase)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.CONFIRM_PURCHASE, callback_data="confirm_bulk_bank")],
        [InlineKeyboardButton(text=texts.CANCEL_PURCHASE, callback_data="cancel_bulk_bank")],
    ])
    await safe_edit_message(callback, confirm_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "confirm_bulk_bank")
async def confirm_bulk_bank_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts):
    """Подтверждение оптовой покупки банка"""
    data = await state.get_data()
    
    section = data.get('section', 'order')
    bank_id = data.get('bank_id')
    quantity = data.get('quantity')
    total_price = Decimal(str(data.get('total_price')))
    
    bank = await BankData.get_bank_by_id_async(session, bank_id, section=section)
    if not bank:
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
    
    # Available uses seller stock, per-order stays worker-side.
    seller_bank = await BankData.get_seller_bank_for_purchase(session, bank_id, quantity=quantity) if section == "available" else None
    if seller_bank:
        seller_order, seller_bank, purchase_error = await _purchase_reserved_seller_order(
            session, callback.from_user.id, mirror_bot_id, bank_id, bank, pricing.final_amount, quantity
        )
        if purchase_error == "balance":
            await callback.answer(texts.INSUFFICIENT_BALANCE_DETAILED.format(required=f"{pricing.final_amount:.2f}", balance=user.balance if user else 0), show_alert=True)
            await state.clear()
            return
        if purchase_error == "stock":
            await callback.answer("❌ Not enough stock for this quantity", show_alert=True)
            await state.clear()
            return
        user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
        await safe_edit_message(
            callback,
            f"✅ *Purchase #{seller_order.id} successful!*\n\n"
            f"🏦 {bank['name']} x{quantity}\n"
            f"💰 Paid: ${pricing.final_amount:.2f}\n"
            f"💳 Balance: ${user.balance:.2f}\n\n"
            f"⚠️ *Press the button below to open your product\\.*\n"
            f"You will have *{BANK_AVAILABLE_CHECK_WINDOW} minutes* to verify\\.\n"
            f"After that, payment is finalized to the seller\\.",
            reply_markup=_bank_reveal_keyboard(seller_order.id, buttons),
            parse_mode="Markdown"
        )
        await callback.answer(texts.ORDER_CREATED_ALERT)
        await state.clear()
        return
    
    # Worker order (no seller stock)
    success = await OrderService.deduct_balance(session, callback.from_user.id, pricing.final_amount)
    if not success:
        await callback.answer(texts.INSUFFICIENT_BALANCE_DETAILED.format(required=f"{pricing.final_amount:.2f}", balance=user.balance if user else 0), show_alert=True)
        await state.clear()
        return
    
    order = await OrderService.create_order(
        session,
        user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
        category="banks",
        service_name=bank_id,
        input_data={"quantity": quantity, "bank_name": bank['name']},
        price=pricing.final_amount,
        original_price=pricing.original_amount,
        coupon_code=pricing.code,
        discount_amount=pricing.discount_amount,
        coupon_application=pricing,
    )
    
    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    
    # Получаем информацию о категории и сервисе
    # Язык берем из базы данных пользователя
    user_language = user.language if user and hasattr(user, 'language') else 'en'
    category_name = ProductTranslations.get_category_name(
        BankData.get_bank_category(bank_id), 
        user_language
    )
    service_name = ProductTranslations.get_service_name(
        bank_id,
        user_language
    )
    
    eta = await ETAService.get_eta_text(session, "bank")
    
    # Формируем название продукта с количеством
    product_display = f"{bank['name']} x{quantity}" if quantity > 1 else bank['name']
    
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


@router.callback_query(F.data == "cancel_bulk_bank")
async def cancel_bulk_bank_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    """Отмена оптовой покупки банка"""
    await state.clear()
    
    # Возвращаем к категориям банков
    await safe_edit_message(
        callback,
        texts.PURCHASE_CANCELLED + "\n\n" + texts.BANKS_MAIN_TEXT,
        reply_markup=banks_main_keyboard(buttons)
    )
    await callback.answer(texts.PURCHASE_CANCELLED)


@router.callback_query(F.data.startswith("bank_buy:"))
async def bank_buy_handler(callback: CallbackQuery, session: AsyncSession, state: FSMContext, mirror_bot_id: int, texts, buttons):
    logger.info(f"[BANKS] Buy handler called: {callback.data}")
    section, bank_id, qty_str = _parse_bank_section_callback(callback.data, "bank_buy")
    if not section:
        logger.error(f"Invalid callback data format: {callback.data}")
        await callback.answer(texts.ERROR_INVALID_DATA_FORMAT, show_alert=True)
        return
    quantity = int(qty_str)
    
    bank = await BankData.get_bank_by_id_async(session, bank_id, section=section)
    if not bank:
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return
    
    # Check stock
    seller_bank = await BankData.get_seller_bank_for_purchase(session, bank_id, quantity=quantity)
    if not seller_bank:
        await callback.answer("❌ This bank is currently out of stock", show_alert=True)
        return
    
    base_price = Decimal(str(bank['price'])) * Decimal(str(quantity))
    
    discount_percent = BulkDiscounts.get_bank_discount(quantity)
    total_price = base_price * (Decimal('1') - Decimal(str(discount_percent)) / Decimal('100'))
    
    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)

    confirm_text = f"{texts.BULK_PURCHASE_TITLE}\n\n"
    confirm_text += f"{texts.BULK_PURCHASE_WARNING}\n\n"
    confirm_text += texts.BULK_PURCHASE_PRODUCT.format(product_name=bank['name']) + "\n"
    confirm_text += texts.BULK_PURCHASE_QUANTITY.format(quantity=quantity) + "\n"
    confirm_text += texts.BULK_PURCHASE_UNIT_PRICE.format(unit_price=bank['price']) + "\n"
    if discount_percent > 0:
        confirm_text += texts.BULK_PURCHASE_DISCOUNT.format(discount_percent=discount_percent) + "\n"
    confirm_text += texts.BULK_PURCHASE_TOTAL.format(total_price=total_price) + "\n\n"
    confirm_text += texts.BULK_PURCHASE_BALANCE.format(balance=user.balance if user else 0) + "\n"
    new_balance = (user.balance if user else Decimal("0")) - total_price
    confirm_text += texts.BULK_PURCHASE_NEW_BALANCE.format(new_balance=new_balance) + "\n\n"
    confirm_text += texts.BULK_PURCHASE_CONFIRM_TEXT.format(quantity=quantity, total_price=total_price)
    _bulk_eta = await ETAService.get_eta_text(session, "bank")
    confirm_text += f"\n\n⏱ *ETA:* {_bulk_eta}"

    await state.update_data(
        section=section,
        bank_id=bank_id,
        quantity=quantity,
        unit_price=float(bank['price']),
        total_price=float(total_price),
        discount_percent=discount_percent,
        checkout_category="banks",
        checkout_service_name=bank_id,
        checkout_base_price=str(total_price),
        checkout_confirm_text=confirm_text,
        checkout_keyboard_type="custom",
        checkout_confirm_callback="confirm_bulk_bank",
        checkout_cancel_callback="cancel_bulk_bank",
        checkout_parse_mode="Markdown",
        selected_coupon_code=None,
        selected_user_coupon_id=None,
    )
    await state.set_state(BankStates.confirm_bulk_purchase)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=texts.CONFIRM_PURCHASE, callback_data="confirm_bulk_bank")],
        [InlineKeyboardButton(text=texts.CANCEL_PURCHASE, callback_data="cancel_bulk_bank")],
    ])

    await safe_edit_message(callback, confirm_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data.startswith("bank_on_name:"))
async def bank_on_name_handler(callback: CallbackQuery, state: FSMContext, texts, buttons):
    """On-Name режим: пользователь вводит имя/SSN, заказ уходит воркерам."""
    section, bank_id = _parse_bank_callback_with_section(callback.data, "bank_on_name")
    if not section:
        await callback.answer(texts.ERROR_INVALID_DATA_FORMAT, show_alert=True)
        return
    bank = BankData.get_bank_by_id(bank_id)
    if not bank:
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return

    await state.update_data(bank_id=bank_id, section=section)
    await state.set_state(BankStates.waiting_name_input)

    await safe_edit_message(
        callback,
        f"📝 *Order by Name — {bank['name']}*\n\n"
        f"💰 *Price:* ${bank['price']}\n\n"
        f"Enter the account holder's full name and optionally SSN/DOB:\n\n"
        f"Format:\n"
        f"`First Last`\n"
        f"or\n"
        f"`First Last / SSN / DOB`\n\n"
        f"Example: `John Smith / 123-45-6789 / 01/15/1985`",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=buttons.CANCEL, callback_data=f"bank_back:{section}:{bank_id}")]
        ]),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(BankStates.waiting_name_input)
async def bank_on_name_input_received(message: Message, state: FSMContext, session: AsyncSession, texts, buttons, mirror_bot_id: int):
    """Получили имя — показываем подтверждение."""
    data = await state.get_data()
    bank_id = data.get("bank_id")
    bank = BankData.get_bank_by_id(bank_id)
    if not bank:
        await state.clear()
        return

    price = Decimal(str(bank["price"]))
    name_input = message.text.strip()
    user = await UserService.get_user(session, message.from_user.id, mirror_bot_id)
    confirm_text = (
        f"✅ *Confirm order by name*\n\n"
        f"🏦 *Bank:* {bank['name']}\n"
        f"📝 *Name/Data:* `{name_input}`\n"
        f"💰 *Price:* ${price:.2f}\n"
        f"💳 *Balance after:* ${(user.balance if user else Decimal('0')) - price:.2f}\n\n"
        f"⏱ *ETA:* {await ETAService.get_eta_text(session, 'bank')}"
    )
    await state.update_data(
        name_input=name_input,
        checkout_category="banks",
        checkout_service_name=bank["name"],
        checkout_base_price=str(price),
        checkout_confirm_text=confirm_text,
        checkout_keyboard_type="custom",
        checkout_confirm_callback="bank_on_name_confirm",
        checkout_cancel_callback="bank_on_name_cancel",
        checkout_parse_mode="Markdown",
        selected_coupon_code=None,
        selected_user_coupon_id=None,
    )
    await state.set_state(BankStates.confirm_on_name)

    await message.answer(
        confirm_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=buttons.CONFIRM_PAY, callback_data="bank_on_name_confirm")],
            [InlineKeyboardButton(text=buttons.CANCEL, callback_data="bank_on_name_cancel")],
        ]),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "bank_on_name_confirm", BankStates.confirm_on_name)
async def bank_on_name_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession, texts, buttons, mirror_bot_id: int):
    """Подтверждение On-Name заказа."""
    data = await state.get_data()
    bank_id = data.get("bank_id")
    name_input = data.get("name_input", "")
    bank = BankData.get_bank_by_id(bank_id)
    if not bank:
        await state.clear()
        await callback.answer("Error: bank not found", show_alert=True)
        return

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    pricing = await CheckoutCouponService.get_checkout_pricing(
        session,
        telegram_user_id=callback.from_user.id,
        state_data=await state.get_data(),
    )
    if not user or user.balance < pricing.final_amount:
        await callback.answer(texts.INSUFFICIENT_BALANCE, show_alert=True)
        await state.clear()
        return

    try:
        success = await OrderService.deduct_balance(session, callback.from_user.id, pricing.final_amount)
        if not success:
            await callback.answer(texts.INSUFFICIENT_BALANCE, show_alert=True)
            await state.clear()
            return
        order = await OrderService.create_order(
            session,
            user_id=callback.from_user.id,
            mirror_bot_id=mirror_bot_id,
            category="banks",
            service_name=bank["name"],
            input_data={"mode": "on_name", "name": name_input, "bank_name": bank["name"], "bank_id": bank_id},
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
            f"🏦 *Bank:* {bank['name']}\n"
            f"📝 *Mode:* On Name\n"
            f"💰 *Paid:* ${pricing.final_amount:.2f}\n"
            f"💳 *Balance:* ${user.balance:.2f}\n\n"
            f"⏱ *ETA:* {await ETAService.get_eta_text(session, 'bank')}\n"
            f"📬 You'll receive the result here when ready.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")]
            ]),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Failed to create on-name bank order: {e}")
        await callback.answer("Error creating order. Please try again.", show_alert=True)
        await state.clear()
    await callback.answer()


@router.callback_query(F.data == "bank_on_name_cancel", BankStates.confirm_on_name)
async def bank_on_name_cancel(callback: CallbackQuery, state: FSMContext, buttons):
    await state.clear()
    await safe_edit_message(callback, "❌ Order cancelled.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back", callback_data="back_main")]
        ]))
    await callback.answer()


@router.callback_query(F.data.startswith("bank_custom:"))
async def bank_custom_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, texts, buttons):
    section, bank_id = _parse_bank_callback_with_section(callback.data, "bank_custom")
    if not section:
        logger.error(f"Invalid callback data format: {callback.data}")
        await callback.answer(texts.ERROR_INVALID_DATA_FORMAT, show_alert=True)
        return
    bank = await BankData.get_bank_by_id_async(session, bank_id, section=section)
    if not bank:
        await callback.answer(texts.ITEM_NOT_FOUND, show_alert=True)
        return
    
    await state.update_data(bank_id=bank_id, section=section)
    await state.set_state(BankStates.waiting_custom_qty)
    
    price_text = texts.BANKS_ITEM_PRICE.format(price=bank['price'])
    discount_text = texts.BANKS_BULK_DISCOUNT.format(
        d3=BulkDiscounts.BANKS_QTY_3,
        d5=BulkDiscounts.BANKS_QTY_5,
        d10=BulkDiscounts.BANKS_QTY_10
    )
    
    await safe_edit_message(
        callback,
        texts.BANKS_ENTER_QTY.format(
            item_name=f"🏦 {bank['name']}",
            price_text=price_text,
            discount_text=discount_text,
            enter_quantity=texts.ENTER_QUANTITY
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=buttons.CANCEL, callback_data=f"bank_item:{section}:{bank_id}")]
        ])
    )
    await callback.answer()


@router.message(BankStates.waiting_custom_qty, F.text)
async def bank_custom_qty_input(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    data = await state.get_data()
    section = data.get("section", "order")
    bank_id = data.get("bank_id")
    
    bank = await BankData.get_bank_by_id_async(session, bank_id, section=section)
    if not bank:
        await message.answer(texts.ITEM_NOT_FOUND)
        await state.clear()
        return
    
    try:
        quantity = int(message.text.strip())
        
        if quantity < 1 or quantity > 100:
            await message.answer(texts.INVALID_QUANTITY)
            return
        
        base_price = Decimal(str(bank['price'])) * Decimal(str(quantity))
        discount_percent = BulkDiscounts.get_bank_discount(quantity)
        total_price = base_price * (Decimal('1') - Decimal(str(discount_percent)) / Decimal('100'))
        
        user = await UserService.get_user(session, message.from_user.id, mirror_bot_id)

        confirm_text = f"{texts.BULK_PURCHASE_TITLE}\n\n"
        confirm_text += f"{texts.BULK_PURCHASE_WARNING}\n\n"
        confirm_text += texts.BULK_PURCHASE_PRODUCT.format(product_name=bank['name']) + "\n"
        confirm_text += texts.BULK_PURCHASE_QUANTITY.format(quantity=quantity) + "\n"
        confirm_text += texts.BULK_PURCHASE_UNIT_PRICE.format(unit_price=bank['price']) + "\n"
        if discount_percent > 0:
            confirm_text += texts.BULK_PURCHASE_DISCOUNT.format(discount_percent=discount_percent) + "\n"
        confirm_text += texts.BULK_PURCHASE_TOTAL.format(total_price=total_price) + "\n\n"
        confirm_text += texts.BULK_PURCHASE_BALANCE.format(balance=user.balance if user else 0) + "\n"
        new_balance = (user.balance if user else Decimal("0")) - total_price
        confirm_text += texts.BULK_PURCHASE_NEW_BALANCE.format(new_balance=new_balance) + "\n\n"
        confirm_text += texts.BULK_PURCHASE_CONFIRM_TEXT.format(quantity=quantity, total_price=total_price)
        _bulk_eta = await ETAService.get_eta_text(session, "bank")
        confirm_text += f"\n\n⏱ *ETA:* {_bulk_eta}"

        await state.update_data(
            section=section,
            bank_id=bank_id,
            quantity=quantity,
            unit_price=float(bank['price']),
            total_price=float(total_price),
            discount_percent=discount_percent,
            checkout_category="banks",
            checkout_service_name=bank_id,
            checkout_base_price=str(total_price),
            checkout_confirm_text=confirm_text,
            checkout_keyboard_type="custom",
            checkout_confirm_callback="confirm_bulk_bank",
            checkout_cancel_callback="cancel_bulk_bank",
            checkout_parse_mode="Markdown",
            selected_coupon_code=None,
            selected_user_coupon_id=None,
        )
        await state.set_state(BankStates.confirm_bulk_purchase)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=texts.CONFIRM_PURCHASE, callback_data="confirm_bulk_bank")],
            [InlineKeyboardButton(text=texts.CANCEL_PURCHASE, callback_data="cancel_bulk_bank")],
        ])

        await message.answer(confirm_text, reply_markup=keyboard, parse_mode="Markdown")
        return
    
    except ValueError:
        await message.answer(texts.INVALID_FORMAT_NUMBER)


@router.callback_query(F.data.startswith("bank_back:"))
async def bank_back_handler(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    section, bank_id = _parse_bank_callback_with_section(callback.data, "bank_back")
    if not section:
        logger.error(f"Invalid callback data format: {callback.data}")
        await callback.answer(texts.ERROR_INVALID_DATA_FORMAT, show_alert=True)
        return

    category = BankData.get_bank_category(bank_id)
    if not category and section == "available":
        bank = await BankData.get_bank_by_id_async(session, bank_id, section=section)
        category = bank.get("category") if bank else None

    if not category:
        await callback.answer(texts.ERROR_GENERAL, show_alert=True)
        return

    category_name = BankData.CATEGORIES[category]["name"]
    if section == "available":
        bank_rows = await BankData.get_available_bank_names(session, category)
        await safe_edit_message(
            callback,
            texts.BANKS_SELECT_ITEM.format(category_name=category_name) + "\n\nSelect bank:",
            reply_markup=banks_bank_names_keyboard(category, section, bank_rows, page=0, buttons_obj=buttons),
        )
    else:
        items = await BankData.get_per_order_items_by_category(session, category)
        await safe_edit_message(
            callback,
            texts.BANKS_SELECT_ITEM.format(category_name=category_name),
            reply_markup=banks_catalog_keyboard(
                category, section, items, page=0, items_per_page=BANK_ITEMS_PER_PAGE, buttons_obj=buttons
            ),
        )
    await callback.answer()


# ============================================
# SELLER ORDER HELPERS
# ============================================

async def _create_seller_order(
    session, buyer_user_id, mirror_bot_id, seller_bank, bank_data, total_price, quantity,
    *, commit: bool = True, instant_delivery: bool = False,
):
    """Create a SellerOrder.

    instant_delivery=True  → status=completed, auto_complete_at set, credentials in result_data
    instant_delivery=False → status=pending_admin (legacy worker flow)
    """
    from shared.database.models import SellerOrder, SystemSetting, User

    buyer_user = await session.scalar(
        select(User).where(
            and_(
                User.user_id == buyer_user_id,
                User.mirror_bot_id == mirror_bot_id,
            )
        )
    )
    marketer_id = getattr(buyer_user, "marketer_id", None)
    marketer_commission_amount = None
    if marketer_id:
        setting = await session.scalar(select(SystemSetting).where(SystemSetting.key == "MARKETER_COMMISSION_RATE"))
        try:
            marketer_rate = Decimal(str(setting.value).strip()) if setting and setting.value not in (None, "") else Decimal("0.10")
        except Exception:
            marketer_rate = Decimal("0.10")
        marketer_commission_amount = (Decimal(str(total_price)) * marketer_rate).quantize(Decimal("0.01"))

    now = datetime.now(timezone.utc)
    check_window = BANK_AVAILABLE_CHECK_WINDOW

    order_kwargs = dict(
        seller_id=seller_bank.seller_id,
        seller_bank_id=seller_bank.id,
        buyer_user_id=buyer_user_id,
        mirror_bot_id=mirror_bot_id,
        product_type=getattr(seller_bank, "product_type", "bank"),
        product_subtype=getattr(seller_bank, "product_subtype", "log"),
        price_for_buyer=total_price,
        price_for_seller=seller_bank.seller_price * quantity,
        quantity=quantity,
        reserved_quantity=quantity,
        reserved_at=now,
        marketer_id=marketer_id,
        marketer_commission_amount=marketer_commission_amount,
    )

    if instant_delivery:
        result_data = {}
        details = getattr(seller_bank, "details", None) or {}
        if details:
            result_data["details"] = details
        result_data["bank_name"] = seller_bank.bank_name
        result_data["bank_code"] = seller_bank.bank_code
        result_data["description"] = getattr(seller_bank, "description", "") or ""
        result_data["instruction"] = getattr(seller_bank, "instruction", "") or ""

        order_kwargs.update(
            status="completed",
            result_data=result_data,
            check_window_minutes=check_window,
            completed_at=now,
            auto_complete_at=now + timedelta(minutes=check_window),
        )
    else:
        order_kwargs["status"] = "pending_admin"

    seller_order = SellerOrder(**order_kwargs)
    session.add(seller_order)
    await session.flush()
    if commit:
        await session.commit()
        await session.refresh(seller_order)
    return seller_order


async def _purchase_reserved_seller_order(session, buyer_user_id, mirror_bot_id, bank_id, bank_data, total_price, quantity):
    seller_bank = await BankData.reserve_seller_bank_for_purchase(session, bank_id, quantity=quantity)
    if not seller_bank:
        await session.rollback()
        return None, None, "stock"

    success = await OrderService.charge_balance(
        session,
        buyer_user_id,
        total_price,
        description=f"Seller bank order {bank_data['name']} x{quantity}",
        commit=False,
    )
    if not success:
        await session.rollback()
        return None, None, "balance"

    try:
        seller_order = await _create_seller_order(
            session,
            buyer_user_id,
            mirror_bot_id,
            seller_bank,
            bank_data,
            total_price,
            quantity,
            commit=False,
            instant_delivery=True,
        )
        await session.commit()
        await session.refresh(seller_order)
        await session.refresh(seller_bank)
        return seller_order, seller_bank, None
    except Exception:
        await session.rollback()
        raise


def _seller_order_created_keyboard(seller_order, seller_bank):
    if getattr(seller_bank, "has_chat", True):
        first_button = InlineKeyboardButton(text="💬 Chat with Seller", callback_data=f"buyer_chat:{seller_order.id}")
    else:
        first_button = InlineKeyboardButton(text="📦 View Order", callback_data=f"buyer_order_detail:{seller_order.id}")
    return InlineKeyboardMarkup(inline_keyboard=[
        [first_button],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")]
    ])


# ============================================
# REVEAL FLOW (Available — instant delivery)
# ============================================

@router.callback_query(F.data.startswith("bank_reveal:"))
async def bank_reveal_handler(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int):
    """Buyer presses 'Open Product' — starts the guarantee timer and shows credentials."""
    from shared.database.models import SellerOrder, SellerBank as SellerBankModel

    order_id = int(callback.data.split(":")[1])
    order = await session.scalar(
        select(SellerOrder).where(SellerOrder.id == order_id)
    )
    if not order or order.buyer_user_id != callback.from_user.id:
        await callback.answer("Order not found", show_alert=True)
        return

    now = datetime.now(timezone.utc)
    if not order.check_started_at:
        order.check_started_at = now
        order.check_expires_at = now + timedelta(minutes=order.check_window_minutes or BANK_AVAILABLE_CHECK_WINDOW)
        order.auto_complete_at = order.check_expires_at
        await session.commit()

    result = order.result_data or {}
    bank_name = result.get("bank_name", "Bank")
    description = result.get("description", "")
    instruction = result.get("instruction", "")
    details = result.get("details", {})

    creds_text = ""
    if details:
        creds_text = "\n".join(f"`{k}: {v}`" for k, v in details.items())
    elif description:
        creds_text = f"`{description}`"

    seller_bank = await session.scalar(
        select(SellerBankModel).where(SellerBankModel.id == order.seller_bank_id)
    )
    has_chat = getattr(seller_bank, "has_chat", True) if seller_bank else True

    text = (
        f"🔐 *Order #{order.id} — {bank_name}*\n\n"
        f"⏱ *You have {order.check_window_minutes or BANK_AVAILABLE_CHECK_WINDOW} minutes to verify\\.*\n"
        f"After that, payment goes to the seller\\.\n\n"
    )
    if instruction:
        text += f"📘 *Instruction:* {instruction}\n\n"
    if creds_text:
        text += f"🔑 *Your product:*\n{creds_text}\n\n"
    text += "Use the buttons below if you have issues\\."

    await safe_edit_message(
        callback,
        text,
        reply_markup=_bank_revealed_keyboard(order.id, seller_bank_has_chat=has_chat),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bank_feedback:"))
async def bank_feedback_handler(callback: CallbackQuery, session: AsyncSession):
    """Buyer rates the seller after purchase."""
    from shared.database.models import SellerOrder

    parts = callback.data.split(":")
    order_id = int(parts[1])
    feedback_status = parts[2]

    order = await session.scalar(
        select(SellerOrder).where(SellerOrder.id == order_id)
    )
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
        "✅ Feedback saved. Thank you!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")],
        ]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bank_report:"))
async def bank_report_handler(callback: CallbackQuery, session: AsyncSession):
    """Buyer reports an issue — opens refund options."""
    from shared.database.models import SellerOrder
    from shared.services.guarantee_policy_service import is_guarantee_active
    from shared.services.seller_conversation_service import get_or_create_conversation

    order_id = int(callback.data.split(":")[1])
    order = await session.scalar(
        select(SellerOrder).where(SellerOrder.id == order_id)
    )
    if not order or order.buyer_user_id != callback.from_user.id:
        await callback.answer("Order not found", show_alert=True)
        return
    if not is_guarantee_active(order.check_expires_at):
        await callback.answer(f"Guarantee window expired ({order.check_window_minutes or BANK_AVAILABLE_CHECK_WINDOW} min)", show_alert=True)
        return

    order.report_status = "reported"
    order.reported_at = datetime.now(timezone.utc)

    conv = await get_or_create_conversation(
        session,
        seller_id=order.seller_id,
        buyer_user_id=order.buyer_user_id,
        mirror_bot_id=order.mirror_bot_id,
        source_order_type="bank",
        source_order_id=order.id,
    )
    await session.commit()

    await safe_edit_message(
        callback,
        "📹 *Refund Request*\n\n"
        "📸 Screenshot proof is required\\.\n"
        "We recommend asking the seller directly first — "
        "most issues are resolved quickly that way\\.\n\n"
        "If the seller doesn't respond, request moderation\\.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Ask Seller First", callback_data=f"buyer_chat_conv:{conv.id}:{order.id}")],
            [InlineKeyboardButton(text="📋 Request Moderation", callback_data=f"bank_moderation:{order.id}")],
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")],
        ]),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bank_moderation:"))
async def bank_moderation_handler(callback: CallbackQuery, session: AsyncSession):
    """Buyer requests moderation for a bank order."""
    from shared.database.models import SellerOrder

    order_id = int(callback.data.split(":")[1])
    order = await session.scalar(
        select(SellerOrder).where(SellerOrder.id == order_id)
    )
    if not order or order.buyer_user_id != callback.from_user.id:
        await callback.answer("Order not found", show_alert=True)
        return
    order.report_status = "moderation_requested"
    await session.commit()

    try:
        from shared.services.admin_notification_service import AdminNotificationService
        await AdminNotificationService.notify_new_dispute(
            order_type="bank",
            order_id=order.id,
            buyer_user_id=callback.from_user.id,
            seller_id=order.seller_id,
        )
    except Exception:
        pass

    await safe_edit_message(
        callback,
        "✅ Moderation request submitted\\.\n\n"
        "📸 Prepare your screenshot proof\\.\n"
        "You will receive a notification when a decision is made\\.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")],
        ]),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("bank_ask_seller:"))
async def bank_ask_seller_handler(callback: CallbackQuery, session: AsyncSession):
    """Buyer opens chat with seller for a bank order."""
    from shared.database.models import SellerOrder
    from shared.services.seller_conversation_service import get_or_create_conversation

    order_id = int(callback.data.split(":")[1])
    order = await session.scalar(
        select(SellerOrder).where(SellerOrder.id == order_id)
    )
    if not order or order.buyer_user_id != callback.from_user.id:
        await callback.answer("Order not found", show_alert=True)
        return

    conv = await get_or_create_conversation(
        session,
        seller_id=order.seller_id,
        buyer_user_id=callback.from_user.id,
        mirror_bot_id=order.mirror_bot_id,
        source_order_type="bank",
        source_order_id=order.id,
    )
    await session.commit()

    await safe_edit_message(
        callback,
        "💬 Open chat with seller:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Open Chat", callback_data=f"buyer_chat_conv:{conv.id}:{order.id}")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data=f"bank_reveal:{order.id}")],
        ]),
    )
    await callback.answer()



@router.callback_query(F.data == "page_info")
async def page_info_noop_handler(callback: CallbackQuery):
    """No-op handler for page navigation indicator buttons (P1-1 fix)"""
    await callback.answer()

