"""
CC (Credit Cards) — все inline-клавиатуры раздела CC.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from mirror_bot.constants.buttons_en import ButtonTexts


def cc_main_keyboard(buttons, categories: list = None, counts: dict | None = None) -> InlineKeyboardMarkup:
    """Главное меню CC — категории из CCCategory + Enroll / OTP / NFC / Selfreg CC."""
    counts = counts or {}
    if not categories:
        categories = [
            {"code": "usa",   "name": "🇺🇸 USA CC"},
            {"code": "world", "name": "🌍 ALL WORLD CC"},
        ]
    enroll_text    = getattr(buttons, "CC_ENROLL",    "🏦 Enroll")
    otp_text       = getattr(buttons, "CC_OTP",       "🔑 OTP")
    nfc_text       = getattr(buttons, "CC_NFC",       "📱 NFC")
    selfreg_text   = getattr(buttons, "CC_SELFREG_CC","🏧 Selfreg CC")
    kb = [
        [InlineKeyboardButton(
            text=ButtonTexts.with_count(c["name"], counts.get(c["code"])),
            callback_data=f"cc_cat:{c['code']}",
        )]
        for c in categories
    ]
    kb.append([InlineKeyboardButton(text=ButtonTexts.with_count(enroll_text,  counts.get("enroll")),    callback_data="cc_enroll")])
    kb.append([InlineKeyboardButton(text=ButtonTexts.with_count(otp_text,     counts.get("otp")),       callback_data="cc_otp")])
    kb.append([InlineKeyboardButton(text=ButtonTexts.with_count(nfc_text,     counts.get("nfc")),       callback_data="cc_nfc")])
    kb.append([InlineKeyboardButton(text=ButtonTexts.with_count(selfreg_text, counts.get("selfreg_cc")),callback_data="cc_selfreg_cc")])
    kb.append([InlineKeyboardButton(text=buttons.BACK, callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


def cc_empty_category_keyboard(buttons) -> InlineKeyboardMarkup:
    """Категория CC пуста."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=getattr(buttons, "CC_NO_ITEMS", "📭 No items available"),
            callback_data="cc_main",
        )],
        [InlineKeyboardButton(text=buttons.BACK, callback_data="cc_main")],
    ])


CC_ITEMS_PER_PAGE = 10
CC_SUBS_EXTRA = 4  # nav rows


def cc_catalog_keyboard(
    buttons,
    items: list,
    category_code: str,
    page: int = 0,
    sort_key: str = "price_asc",
    bin_filter: str | None = None,
    zip_filter: str | None = None,
) -> InlineKeyboardMarkup:
    """Список товаров внутри категории CC с пагинацией и сортировкой."""
    from mirror_bot.utils.catalog_pagination import clamp_page

    items = list(items)
    total_pages = max(1, (len(items) + CC_ITEMS_PER_PAGE - 1) // CC_ITEMS_PER_PAGE)
    page = clamp_page(page, len(items), CC_ITEMS_PER_PAGE)
    start = page * CC_ITEMS_PER_PAGE
    chunk = items[start : start + CC_ITEMS_PER_PAGE]

    bf = bin_filter or "-"
    zf = zip_filter or "-"

    rows = [
        [InlineKeyboardButton(
            text=f"{item['name'][:58]}{'…' if len(item['name']) > 58 else ''}",
            callback_data=f"cc_item:{category_code}:{item['id']}:{bf}:{zf}",
        )]
        for item in chunk
    ]

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="⬅️ Prev",
            callback_data=f"cc_listpg:{category_code}:{page - 1}:{sort_key}:{bf}:{zf}",
        ))
    nav.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="page_info"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            text="Next ➡️",
            callback_data=f"cc_listpg:{category_code}:{page + 1}:{sort_key}:{bf}:{zf}",
        ))
    if nav:
        rows.append(nav)

    sort_next = "price_desc" if sort_key == "price_asc" else "price_asc"
    sort_label = "💲 Price ↑" if sort_key == "price_asc" else "💲 Price ↓"
    rows.append([
        InlineKeyboardButton(text=sort_label, callback_data=f"cc_listpg:{category_code}:0:{sort_next}:{bf}:{zf}"),
    ])
    rows.append([
        InlineKeyboardButton(text="🔍 BIN", callback_data=f"cc_ask_bin:{category_code}:{sort_key}:{zf}"),
        InlineKeyboardButton(text="🔍 ZIP", callback_data=f"cc_ask_zip:{category_code}:{sort_key}:{bf}"),
    ])
    if bin_filter or zip_filter:
        rows.append([
            InlineKeyboardButton(text="✖ Clear filters", callback_data=f"cc_listpg:{category_code}:0:{sort_key}:-:-"),
        ])
    rows.append([InlineKeyboardButton(text=buttons.BACK, callback_data="cc_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cc_item_detail_keyboard(
    buttons, item: dict, category_code: str, back_callback: str | None = None,
) -> InlineKeyboardMarkup:
    """Карточка товара CC — кнопка покупки (только для seller-товаров) + назад."""
    rows = []
    back_cb = back_callback or f"cc_cat:{category_code}"
    if item.get("source") == "seller" and item.get("seller_item_id"):
        rows.append([InlineKeyboardButton(
            text=getattr(buttons, "CC_BUY", "🛒 Buy"),
            callback_data=f"cc_buy:{item['seller_item_id']}:{category_code}",
        )])
    rows.append([InlineKeyboardButton(text=buttons.BACK, callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cc_buy_confirm_keyboard(buttons, item_id: int, category_code: str) -> InlineKeyboardMarkup:
    """Подтверждение покупки CC."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.CONFIRM, callback_data=f"cc_buy_confirm:{item_id}")],
        [InlineKeyboardButton(text=buttons.CANCEL,  callback_data=f"cc_cat:{category_code}")],
    ])


def cc_result_keyboard(buttons, order_id: int) -> InlineKeyboardMarkup:
    """Клавиатура после успешной покупки CC — только репорт в модерацию (без чата с продавцом)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=getattr(buttons, "CC_REPORT_ISSUE", "⚠️ Report Issue (Screenshot)"),
            callback_data=f"cc_report:{order_id}",
        )],
        [InlineKeyboardButton(text=getattr(buttons, "BACK", "🏠 Main Menu"), callback_data="back_main")],
    ])


def cc_specials_keyboard(buttons, items_rows: list, back_callback: str = "cc_main") -> InlineKeyboardMarkup:
    """Список CC specials (Selfreg CC / Enroll / OTP / NFC) + кнопка назад."""
    back_text = getattr(buttons, "CC_BACK_TO_CC", "⬅️ Back to CC")
    rows = items_rows + [[InlineKeyboardButton(text=back_text, callback_data=back_callback)]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cc_feedback_done_keyboard(buttons) -> InlineKeyboardMarkup:
    """После сохранения отзыва CC."""
    back_text = getattr(buttons, "BACK_TO_MENU", getattr(buttons, "BACK", "Back"))
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=back_text, callback_data="back_main")],
    ])


def cc_report_done_keyboard(buttons) -> InlineKeyboardMarkup:
    """После подачи репорта CC — только назад (нет чата, модерация решает)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=getattr(buttons, "BACK", "🏠 Main Menu"), callback_data="back_main")],
    ])
