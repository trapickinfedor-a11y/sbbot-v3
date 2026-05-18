from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from mirror_bot.constants.buttons_en import ButtonTexts
from mirror_bot.services.menu_counts_service import MenuCountService
from mirror_bot.services.order_service import OrderService
from mirror_bot.services.checkout_coupon_service import CheckoutCouponService
from mirror_bot.services.user_service import UserService
from mirror_bot.utils.message_utils import safe_edit_message
from mirror_bot.states.order import OrderStates
from shared.database.models import (
    Seller,
    SelfregCCCategory,
    SellerBankItem,
    SellerBankOrder,
    SellerCheckItem,
    SellerCheckOrder,
    SellerEnrollItem,
    SellerEnrollOrder,
    EnrollCategory,
    SellerLogsItem,
    SellerLogsOrder,
    SellerNFCItem,
    SellerNFCOrder,
    SellerOTPItem,
    SellerOTPOrder,
    SellerSelfregCCItem,
    SellerSelfregCCOrder,
    User,
)
from mirror_bot.utils.catalog_pagination import clamp_page
from shared.services.guarantee_policy_service import format_guarantee_window, is_guarantee_active
from shared.services.nocodb_service import NocoDBService
from shared.services.seller_conversation_service import get_or_create_conversation
from shared.utils.seller_card_renderers import (
    render_check_description,
    render_enroll_description,
    render_logs_description,
    render_nfc_description,
    render_otp_description,
    render_selfreg_ba_description,
    render_selfreg_cc_description,
)

router = Router(name="seller_specials")


async def open_specials_catalog_message(message, session: AsyncSession, kind: str) -> None:
    """Open specials catalog for a given kind from a Message (called by dynamic_menu)."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kind = _normalize_kind(kind)
    meta = SPECIALS.get(kind)
    if not meta:
        await message.answer(f"Category not found: {kind}")
        return
    if kind == "selfreg_cc":
        cats = list(
            (await session.execute(
                select(SelfregCCCategory).where(SelfregCCCategory.is_active == True).order_by(
                    SelfregCCCategory.position, SelfregCCCategory.id
                )
            )).scalars().all()
        )
        cnt_map = await _selfreg_cc_category_counts(session)
        rows = []
        for c in cats[:8]:
            rows.append([
                InlineKeyboardButton(
                    text=ButtonTexts.with_count(c.name[:35], cnt_map.get(c.id, 0)),
                    callback_data=f"seller_specials_selfreg_cc_cat:{c.code}:0:price_asc",
                )
            ])
        if not rows:
            rows.append([InlineKeyboardButton(text="No categories", callback_data="back_main")])
        rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back_main")])
        await message.answer(
            f"{meta['label']} catalog\n\nChoose bank:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        )
        return
    items = list((await session.execute(
        select(meta["model"])
        .join(Seller)
        .where(
            meta["model"].is_active == True,
            meta["model"].is_in_stock == True,
            meta["model"].moderation_status == "approved",
            Seller.is_approved == True,
            Seller.is_active == True,
        )
        .limit(20)
    )).scalars().all())
    if not items:
        await message.answer(
            f"{meta['label']}\n\nNo items available.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Back", callback_data="back_main")]
            ]),
        )
        return
    rows = [
        [InlineKeyboardButton(
            text=f"{_item_title(item)} | ${float(_item_price(item)):.2f}",
            callback_data=f"seller_specials_detail:{kind}:{item.id}",
        )]
        for item in items
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back_main")])
    await message.answer(
        f"{meta['label']}\n\nSelect item:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )

KIND_ALIASES = {
    "check": "checks",
    "otp_card": "otp",
}

SPECIALS = {
    "nfc": {
        "label": "📱 NFC",
        "count_key": "nfc",
        "model": SellerNFCItem,
        "order_model": SellerNFCOrder,
        "window": 60,
        "schema": "modern",
        "allow_chat": True,
        "chat_before_purchase": True,
        "refund_type": "video_seller_first",
        "use_reveal": True,
    },
    "enroll": {
        "label": "🏦 Enroll",
        "count_key": "enroll",
        "model": SellerEnrollItem,
        "order_model": SellerEnrollOrder,
        "window": 60,
        "schema": "legacy",
        "allow_chat": True,
        "chat_before_purchase": True,
        "refund_type": "video_seller_first",
        "use_reveal": True,
    },
    "selfreg_ba": {
        "label": "🏧 Selfreg BA",
        "count_key": "selfreg_ba",
        "model": SellerBankItem,
        "order_model": SellerBankOrder,
        "window": 24 * 60,
        "schema": "legacy",
        "allow_chat": True,
        "chat_before_purchase": False,
        "refund_type": "video_seller_first",
    },
    "logs": {
        "label": "📋 Logs",
        "count_key": "logs",
        "model": SellerLogsItem,
        "order_model": SellerLogsOrder,
        "window": 24 * 60,
        "schema": "legacy",
        "allow_chat": True,
        "chat_before_purchase": True,
        "refund_type": "video_seller_first",
    },
    "otp": {
        "label": "📲 OTP Card",
        "count_key": "otp",
        "model": SellerOTPItem,
        "order_model": SellerOTPOrder,
        "window": 60,
        "schema": "modern",
        "allow_chat": True,
        "chat_before_purchase": True,
        "refund_type": "video_seller_first",
        "use_reveal": True,
    },
    "selfreg_cc": {
        "label": "💳 Selfreg CC",
        "count_key": "selfreg_cc",
        "model": SellerSelfregCCItem,
        "order_model": SellerSelfregCCOrder,
        "window": 24 * 60,
        "schema": "modern",
        "allow_chat": True,
        "chat_before_purchase": True,
        "refund_type": "video_seller_first",
    },
    "checks": {
        "label": "📄 Checks",
        "count_key": "checks",
        "model": SellerCheckItem,
        "order_model": SellerCheckOrder,
        "window": 24 * 60,
        "schema": "modern",
        "allow_chat": False,
        "chat_before_purchase": False,
        "refund_type": "moderation_only",
    },
    "merchants": {
        "label": "🏪 Merchants",
        "count_key": "merchants",
        "model": SellerSelfregCCItem,   # placeholder until MerchantItem model is ready
        "order_model": SellerSelfregCCOrder,
        "window": 24 * 60,
        "schema": "modern",
        "allow_chat": True,
        "chat_before_purchase": True,
        "refund_type": "video_seller_first",
    },
}

CHECK_TYPE_LABELS = {
    "personal": "Personal",
    "business": "Business",
    "payroll": "Payroll",
    "cashier": "Cashier",
}


def _specials_main_keyboard(counts: dict[str, int | str] | None = None) -> InlineKeyboardMarkup:
    counts = counts or {}
    rows: list[list[InlineKeyboardButton]] = []
    current_row: list[InlineKeyboardButton] = []
    for kind, meta in SPECIALS.items():
        current_row.append(
            InlineKeyboardButton(
                text=ButtonTexts.with_count(meta["label"], counts.get(meta["count_key"])),
                callback_data=f"seller_specials_list:{kind}",
            )
        )
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="back_to_profile")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _special_result_keyboard(kind: str, order_id: int, allow_chat: bool = True) -> InlineKeyboardMarkup:
    rows = []
    if allow_chat:
        rows.append([InlineKeyboardButton(text="💬 Ask Seller", callback_data=f"seller_specials_ask_seller:{kind}:{order_id}")])
    rows += [
        [InlineKeyboardButton(text="📹 Refund Request", callback_data=f"seller_specials_report:{kind}:{order_id}")],
        [InlineKeyboardButton(text="👍 Like", callback_data=f"seller_specials_feedback:{kind}:{order_id}:liked")],
        [InlineKeyboardButton(text="👎 Dislike", callback_data=f"seller_specials_feedback:{kind}:{order_id}:disliked")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="seller_specials_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _special_refund_options_keyboard(kind: str, order_id: int, conv_id: int) -> InlineKeyboardMarkup:
    """After refund request: ask seller first OR go straight to moderation."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Ask Seller First", callback_data=f"buyer_chat_conv:{conv_id}:{order_id}")],
        [InlineKeyboardButton(text="📋 Request Moderation", callback_data=f"seller_specials_moderation:{kind}:{order_id}")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data="seller_specials_main")],
    ])


def _format_check_type_label(check_type: str) -> str:
    normalized = (check_type or "").strip().lower()
    return CHECK_TYPE_LABELS.get(normalized, normalized.replace("_", " ").title() or "Other")


async def _load_check_type_counts(session: AsyncSession) -> dict[str, int]:
    rows = (
        await session.execute(
            select(SellerCheckItem.check_type, func.count(SellerCheckItem.id))
            .join(Seller)
            .where(
                SellerCheckItem.moderation_status == "approved",
                SellerCheckItem.is_active == True,
                SellerCheckItem.is_in_stock == True,
                Seller.is_approved == True,
                Seller.is_active == True,
            )
            .group_by(SellerCheckItem.check_type)
        )
    ).all()
    counts = {str(check_type or "").strip().lower(): int(total or 0) for check_type, total in rows if check_type}
    for known_type in CHECK_TYPE_LABELS:
        counts.setdefault(known_type, 0)
    return counts


def _checks_type_keyboard(counts: dict[str, int]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [[
        InlineKeyboardButton(
            text=ButtonTexts.with_count("All checks", sum(counts.values())),
            callback_data="seller_specials_checks_type:all:0:price_asc",
        )
    ]]
    ordered = [key for key in CHECK_TYPE_LABELS if key in counts]
    extra = sorted(key for key in counts if key not in CHECK_TYPE_LABELS)
    for check_type in ordered + extra:
        rows.append([
            InlineKeyboardButton(
                text=ButtonTexts.with_count(_format_check_type_label(check_type), counts.get(check_type)),
                callback_data=f"seller_specials_checks_type:{check_type}:0:price_asc",
            )
        ])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="seller_specials_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _item_title(item) -> str:
    return (
        getattr(item, "item_name", None)
        or getattr(item, "bank_name", None)
        or getattr(item, "bank", None)
        or getattr(item, "portal", None)
        or str(getattr(item, "id", "?"))
    )


def _item_price(item) -> Decimal:
    for attr in ("buyer_price", "final_price", "seller_price", "price"):
        v = getattr(item, attr, None)
        if v is not None:
            return Decimal(str(v))
    return Decimal("0")


def _parse_mode_for_kind(kind: str) -> str | None:
    return "HTML" if kind in {"enroll", "selfreg_ba", "logs"} else None


def _order_guarantee_until(order):
    return getattr(order, "check_expires_at", None) or getattr(order, "guarantee_until", None)


def _order_belongs_to_user(order, buyer: User | None) -> bool:
    if order is None or buyer is None:
        return False
    if hasattr(order, "buyer_user_id"):
        return order.buyer_user_id == buyer.user_id
    return getattr(order, "buyer_id", None) == buyer.id


def _normalize_kind(kind: str) -> str:
    return KIND_ALIASES.get(kind, kind)


def _price_sort(items: list, sort_key: str, price_getter) -> list:
    rev = sort_key == "price_desc"
    return sorted(items, key=lambda x: float(price_getter(x)), reverse=rev)


async def _nfc_type_counts(session: AsyncSession) -> dict[str, int]:
    rows = (
        await session.execute(
            select(SellerNFCItem.nfc_type, func.count(SellerNFCItem.id))
            .join(Seller)
            .where(
                SellerNFCItem.moderation_status == "approved",
                SellerNFCItem.is_active == True,
                SellerNFCItem.is_in_stock == True,
                Seller.is_approved == True,
                Seller.is_active == True,
            )
            .group_by(SellerNFCItem.nfc_type)
        )
    ).all()
    out = {"ap": 0, "gp": 0, "other": 0}
    for t, c in rows:
        k = (t or "").lower()
        if k in out:
            out[k] = int(c or 0)
    return out


async def _enroll_category_counts(session: AsyncSession) -> dict[int, int]:
    rows = (
        await session.execute(
            select(SellerEnrollItem.enroll_category_id, func.count(SellerEnrollItem.id))
            .join(Seller)
            .where(
                SellerEnrollItem.moderation_status == "approved",
                SellerEnrollItem.is_active == True,
                SellerEnrollItem.is_in_stock == True,
                Seller.is_approved == True,
                Seller.is_active == True,
            )
            .group_by(SellerEnrollItem.enroll_category_id)
        )
    ).all()
    return {int(cid): int(cnt or 0) for cid, cnt in rows if cid is not None}


async def _selfreg_cc_category_counts(session: AsyncSession) -> dict[int, int]:
    rows = (
        await session.execute(
            select(SellerSelfregCCItem.selfreg_cc_category_id, func.count(SellerSelfregCCItem.id))
            .join(Seller)
            .where(
                SellerSelfregCCItem.moderation_status == "approved",
                SellerSelfregCCItem.is_active == True,
                SellerSelfregCCItem.is_in_stock == True,
                Seller.is_approved == True,
                Seller.is_active == True,
            )
            .group_by(SellerSelfregCCItem.selfreg_cc_category_id)
        )
    ).all()
    return {int(cid): int(cnt or 0) for cid, cnt in rows if cid is not None}


def _logs_price_condition(filter_key: str):
    fk = (filter_key or "all").lower()
    if fk == "all":
        return True
    if fk == "0_25":
        return and_(SellerLogsItem.price >= 0, SellerLogsItem.price <= 25)
    if fk == "25_50":
        return and_(SellerLogsItem.price > 25, SellerLogsItem.price <= 50)
    if fk == "50_100":
        return and_(SellerLogsItem.price > 50, SellerLogsItem.price <= 100)
    if fk == "100_plus":
        return SellerLogsItem.price > 100
    return True


def _describe_item(kind: str, item) -> str:
    if kind == "nfc":
        return render_nfc_description(item)
    if kind == "enroll":
        return render_enroll_description(item)
    if kind == "selfreg_ba":
        return render_selfreg_ba_description(item)
    if kind == "logs":
        return render_logs_description(item)
    if kind == "otp":
        return render_otp_description(item)
    if kind == "selfreg_cc":
        return render_selfreg_cc_description(item)
    return render_check_description(item)


def _build_result_text(kind: str, item) -> str:
    details = _describe_item(kind, item)
    if kind == "checks":
        return f"{details}\nDate: {getattr(item, 'check_date', None) or '-'}"
    if kind in {"enroll", "selfreg_ba", "logs"} and getattr(item, "raw_data", None):
        return f"{details}\n\n<pre>{escape(str(item.raw_data))}</pre>"
    return details


@router.callback_query(F.data == "seller_specials_main")
async def seller_specials_main(callback: CallbackQuery, session: AsyncSession):
    counts = (await MenuCountService.get_seller_specials_counts(session)).get("by_kind") or {}
    await safe_edit_message(
        callback,
        "🛍 *Seller Specials*\n\nChoose a product family:",
        reply_markup=_specials_main_keyboard(counts),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_specials_list:"))
async def seller_specials_list(callback: CallbackQuery, session: AsyncSession):
    kind = _normalize_kind(callback.data.split(":")[1])
    meta = SPECIALS.get(kind)
    if not meta:
        await callback.answer("Unknown category", show_alert=True)
        return
    if kind == "checks":
        counts = await _load_check_type_counts(session)
        await safe_edit_message(
            callback,
            f"{meta['label']} catalog\n\nChoose check type:",
            reply_markup=_checks_type_keyboard(counts),
            parse_mode=None,
        )
        await callback.answer()
        return
    if kind == "nfc":
        counts = await _nfc_type_counts(session)
        rows = [
            [InlineKeyboardButton(
                text=ButtonTexts.with_count("🍎 Apple Pay", counts.get("ap")),
                callback_data="seller_specials_nfc:ap:0:price_asc",
            )],
            [InlineKeyboardButton(
                text=ButtonTexts.with_count("🤖 Google Pay", counts.get("gp")),
                callback_data="seller_specials_nfc:gp:0:price_asc",
            )],
            [InlineKeyboardButton(
                text=ButtonTexts.with_count("📎 Other", counts.get("other")),
                callback_data="seller_specials_nfc:other:0:price_asc",
            )],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="seller_specials_main")],
        ]
        await safe_edit_message(
            callback,
            f"{meta['label']} catalog\n\nChoose NFC type:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
            parse_mode=None,
        )
        await callback.answer()
        return
    if kind == "enroll":
        cats = list(
            (await session.execute(
                select(EnrollCategory).where(EnrollCategory.is_active == True).order_by(
                    EnrollCategory.position, EnrollCategory.id
                )
            )).scalars().all()
        )
        cnt_map = await _enroll_category_counts(session)
        rows = []
        for c in cats[:30]:
            rows.append([
                InlineKeyboardButton(
                    text=ButtonTexts.with_count(c.name[:35], cnt_map.get(c.id, 0)),
                    callback_data=f"seller_specials_enroll_cat:{c.code}:0:price_asc",
                )
            ])
        if not rows:
            rows.append([InlineKeyboardButton(text="No categories", callback_data="seller_specials_main")])
        rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="seller_specials_main")])
        await safe_edit_message(
            callback,
            f"{meta['label']} catalog\n\nChoose portal:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
            parse_mode=None,
        )
        await callback.answer()
        return
    if kind == "otp":
        await _render_otp_list(callback, session, page=0, sort_key="price_asc")
        await callback.answer()
        return
    if kind == "logs":
        await _render_logs_list(callback, session, page=0, sort_key="price_asc", price_filter="all")
        await callback.answer()
        return
    if kind == "selfreg_cc":
        cats = list(
            (await session.execute(
                select(SelfregCCCategory).where(SelfregCCCategory.is_active == True).order_by(
                    SelfregCCCategory.position, SelfregCCCategory.id
                )
            )).scalars().all()
        )
        cnt_map = await _selfreg_cc_category_counts(session)
        SELFREG_CC_CATS_PER_PAGE = 8
        rows = []
        for c in cats[:SELFREG_CC_CATS_PER_PAGE]:
            rows.append([
                InlineKeyboardButton(
                    text=ButtonTexts.with_count(c.name[:35], cnt_map.get(c.id, 0)),
                    callback_data=f"seller_specials_selfreg_cc_cat:{c.code}:0:price_asc",
                )
            ])
        if not rows:
            rows.append([InlineKeyboardButton(text="No categories", callback_data="seller_specials_main")])
        rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="seller_specials_main")])
        await safe_edit_message(
            callback,
            f"{meta['label']} catalog\n\nChoose bank:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
            parse_mode=None,
        )
        await callback.answer()
        return
    items = list((await session.execute(
        select(meta["model"]).where(
            meta["model"].moderation_status == "approved",
            meta["model"].is_active == True,
            meta["model"].is_in_stock == True,
        ).order_by(meta["model"].created_at.desc()).limit(30)
    )).scalars().all())
    rows = [
        [
            InlineKeyboardButton(
                text=f"{_item_title(item)} | ${float(_item_price(item)):.2f}",
                callback_data=f"seller_specials_detail:{kind}:{item.id}",
            )
        ]
        for item in items
    ]
    if not rows:
        rows.append([InlineKeyboardButton(text="No items available", callback_data="seller_specials_main")])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="seller_specials_main")])
    await safe_edit_message(
        callback,
        f"{meta['label']} catalog\n\nSelect item:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode=None,
    )
    await callback.answer()


async def _render_otp_list(callback: CallbackQuery, session: AsyncSession, page: int, sort_key: str):
    meta = SPECIALS["otp"]
    q = (
        select(meta["model"])
        .join(Seller)
        .where(
            meta["model"].moderation_status == "approved",
            meta["model"].is_active == True,
            meta["model"].is_in_stock == True,
            Seller.is_approved == True,
            Seller.is_active == True,
        )
    )
    items = list((await session.execute(q)).scalars().all())
    items = _price_sort(items, sort_key, lambda x: float(_item_price(x)))
    per_page = 10
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    page = clamp_page(page, len(items), per_page)
    chunk = items[page * per_page : page * per_page + per_page]
    rows = []
    for it in chunk:
        bal = float(getattr(it, "balance", 0) or 0)
        pr = float(_item_price(it))
        sms = getattr(it, "sms_access_type", "") or ""
        sms_hint = " ·seller" if sms == "seller_mediated" else " ·acct" if sms == "account_access" else ""
        label = f"{getattr(it, 'bank_name', '')} ${bal:,.0f}{sms_hint} | ${pr:.2f}"[:64]
        rows.append([
            InlineKeyboardButton(text=label, callback_data=f"seller_specials_detail:otp:{it.id}"),
        ])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Prev", callback_data=f"seller_specials_otp_pg:{page - 1}:{sort_key}"))
    nav.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="page_info"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"seller_specials_otp_pg:{page + 1}:{sort_key}"))
    if nav:
        rows.append(nav)
    sort_next = "price_desc" if sort_key == "price_asc" else "price_asc"
    rows.append([
        InlineKeyboardButton(
            text="💲 Price ↑" if sort_key == "price_asc" else "💲 Price ↓",
            callback_data=f"seller_specials_otp_pg:0:{sort_next}",
        ),
    ])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="seller_specials_main")])
    await safe_edit_message(
        callback,
        f"{meta['label']} catalog\n\nSelect item:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode=None,
    )


async def _render_logs_list(
    callback: CallbackQuery, session: AsyncSession, page: int, sort_key: str, price_filter: str,
):
    meta = SPECIALS["logs"]
    cond = [
        SellerLogsItem.moderation_status == "approved",
        SellerLogsItem.is_active == True,
        SellerLogsItem.is_in_stock == True,
    ]
    cond.append(_logs_price_condition(price_filter))
    q = select(meta["model"]).join(Seller).where(
        Seller.is_approved == True,
        Seller.is_active == True,
        *cond,
    )
    items = list((await session.execute(q)).scalars().all())
    items = _price_sort(items, sort_key, lambda x: float(_item_price(x)))
    per_page = 10
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    page = clamp_page(page, len(items), per_page)
    chunk = items[page * per_page : page * per_page + per_page]
    rows = [
        [InlineKeyboardButton(
            text=f"{getattr(it, 'bank', '')} | ${float(_item_price(it)):.2f}"[:60],
            callback_data=f"seller_specials_detail:logs:{it.id}",
        )]
        for it in chunk
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="⬅️ Prev",
            callback_data=f"seller_specials_logs_pg:{page - 1}:{sort_key}:{price_filter}",
        ))
    nav.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="page_info"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            text="Next ➡️",
            callback_data=f"seller_specials_logs_pg:{page + 1}:{sort_key}:{price_filter}",
        ))
    if nav:
        rows.append(nav)
    sort_next = "price_desc" if sort_key == "price_asc" else "price_asc"
    rows.append([
        InlineKeyboardButton(
            text="💲 Price ↑" if sort_key == "price_asc" else "💲 Price ↓",
            callback_data=f"seller_specials_logs_pg:0:{sort_next}:{price_filter}",
        ),
    ])
    rows.append([
        InlineKeyboardButton(text="All $", callback_data=f"seller_specials_logs_pg:0:{sort_key}:all"),
        InlineKeyboardButton(text="$0–25", callback_data=f"seller_specials_logs_pg:0:{sort_key}:0_25"),
        InlineKeyboardButton(text="$25–50", callback_data=f"seller_specials_logs_pg:0:{sort_key}:25_50"),
    ])
    rows.append([
        InlineKeyboardButton(text="$50–100", callback_data=f"seller_specials_logs_pg:0:{sort_key}:50_100"),
        InlineKeyboardButton(text="$100+", callback_data=f"seller_specials_logs_pg:0:{sort_key}:100_plus"),
    ])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="seller_specials_main")])
    await safe_edit_message(
        callback,
        f"{meta['label']} catalog\n\nFilter: {price_filter}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode=None,
    )


@router.callback_query(F.data.startswith("seller_specials_nfc:"))
async def seller_specials_nfc_type(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    nfc_type = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 0
    sort_key = parts[3] if len(parts) > 3 else "price_asc"
    q = (
        select(SellerNFCItem)
        .join(Seller)
        .where(
            func.lower(SellerNFCItem.nfc_type) == nfc_type.lower(),
            SellerNFCItem.moderation_status == "approved",
            SellerNFCItem.is_active == True,
            SellerNFCItem.is_in_stock == True,
            Seller.is_approved == True,
            Seller.is_active == True,
        )
    )
    items = list((await session.execute(q)).scalars().all())
    items = _price_sort(items, sort_key, lambda x: float(_item_price(x)))
    per_page = 10
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    page = clamp_page(page, len(items), per_page)
    chunk = items[page * per_page : page * per_page + per_page]
    rows = [
        [InlineKeyboardButton(
            text=f"{getattr(it, 'bank_name', '')} {getattr(it, 'country', '')} | ${float(_item_price(it)):.2f}"[:64],
            callback_data=f"seller_specials_detail:nfc:{it.id}",
        )]
        for it in chunk
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="⬅️ Prev",
            callback_data=f"seller_specials_nfc:{nfc_type}:{page - 1}:{sort_key}",
        ))
    nav.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="page_info"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            text="Next ➡️",
            callback_data=f"seller_specials_nfc:{nfc_type}:{page + 1}:{sort_key}",
        ))
    if nav:
        rows.append(nav)
    sort_next = "price_desc" if sort_key == "price_asc" else "price_asc"
    rows.append([
        InlineKeyboardButton(
            text="💲 Price ↑" if sort_key == "price_asc" else "💲 Price ↓",
            callback_data=f"seller_specials_nfc:{nfc_type}:0:{sort_next}",
        ),
    ])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="seller_specials_list:nfc")])
    await safe_edit_message(
        callback,
        f"📱 NFC catalog ({nfc_type.upper()})\n\nSelect item:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode=None,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_specials_enroll_cat:"))
async def seller_specials_enroll_cat(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    code = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 0
    sort_key = parts[3] if len(parts) > 3 else "price_asc"
    cat = await session.scalar(select(EnrollCategory).where(EnrollCategory.code == code))
    if not cat:
        await callback.answer("Category not found", show_alert=True)
        return
    q = (
        select(SellerEnrollItem)
        .join(Seller)
        .where(
            SellerEnrollItem.enroll_category_id == cat.id,
            SellerEnrollItem.moderation_status == "approved",
            SellerEnrollItem.is_active == True,
            SellerEnrollItem.is_in_stock == True,
            Seller.is_approved == True,
            Seller.is_active == True,
        )
    )
    items = list((await session.execute(q)).scalars().all())
    items = _price_sort(items, sort_key, lambda x: float(_item_price(x)))
    per_page = 12
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    page = clamp_page(page, len(items), per_page)
    chunk = items[page * per_page : page * per_page + per_page]
    rows = [
        [InlineKeyboardButton(
            text=(
                f"{getattr(it, 'bank_name', None) or getattr(it, 'portal', '')} "
                f"${float(getattr(it, 'balance', 0) or 0):,.0f} | ${float(_item_price(it)):.2f}"
            )[:64],
            callback_data=f"seller_specials_detail:enroll:{it.id}",
        )]
        for it in chunk
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="⬅️ Prev",
            callback_data=f"seller_specials_enroll_cat:{code}:{page - 1}:{sort_key}",
        ))
    nav.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="page_info"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            text="Next ➡️",
            callback_data=f"seller_specials_enroll_cat:{code}:{page + 1}:{sort_key}",
        ))
    if nav:
        rows.append(nav)
    sort_next = "price_desc" if sort_key == "price_asc" else "price_asc"
    rows.append([
        InlineKeyboardButton(
            text="💲 Price ↑" if sort_key == "price_asc" else "💲 Price ↓",
            callback_data=f"seller_specials_enroll_cat:{code}:0:{sort_next}",
        ),
    ])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="seller_specials_list:enroll")])
    await safe_edit_message(
        callback,
        f"🏦 Enroll — {cat.name}\n\nSelect item:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode=None,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_specials_selfreg_cc_cat:"))
async def seller_specials_selfreg_cc_cat(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    code = parts[1]
    page = int(parts[2]) if len(parts) > 2 else 0
    sort_key = parts[3] if len(parts) > 3 else "price_asc"
    cat = await session.scalar(select(SelfregCCCategory).where(SelfregCCCategory.code == code))
    if not cat:
        await callback.answer("Category not found", show_alert=True)
        return
    q = (
        select(SellerSelfregCCItem)
        .join(Seller)
        .where(
            SellerSelfregCCItem.selfreg_cc_category_id == cat.id,
            SellerSelfregCCItem.moderation_status == "approved",
            SellerSelfregCCItem.is_active == True,
            SellerSelfregCCItem.is_in_stock == True,
            Seller.is_approved == True,
            Seller.is_active == True,
        )
    )
    items = list((await session.execute(q)).scalars().all())
    items = _price_sort(items, sort_key, lambda x: float(_item_price(x)))
    per_page = 15
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    page = clamp_page(page, len(items), per_page)
    chunk = items[page * per_page : page * per_page + per_page]
    rows = [
        [InlineKeyboardButton(
            text=(
                f"{getattr(it, 'bank_name', '') or getattr(it, 'item_name', '')} "
                f"| ${float(_item_price(it)):.2f}"
            )[:64],
            callback_data=f"seller_specials_detail:selfreg_cc:{it.id}",
        )]
        for it in chunk
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="⬅️ Prev",
            callback_data=f"seller_specials_selfreg_cc_cat:{code}:{page - 1}:{sort_key}",
        ))
    nav.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="page_info"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            text="Next ➡️",
            callback_data=f"seller_specials_selfreg_cc_cat:{code}:{page + 1}:{sort_key}",
        ))
    if nav:
        rows.append(nav)
    sort_next = "price_desc" if sort_key == "price_asc" else "price_asc"
    rows.append([
        InlineKeyboardButton(
            text="💲 Price ↑" if sort_key == "price_asc" else "💲 Price ↓",
            callback_data=f"seller_specials_selfreg_cc_cat:{code}:0:{sort_next}",
        ),
    ])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="seller_specials_list:selfreg_cc")])
    await safe_edit_message(
        callback,
        f"💳 Selfreg CC — {cat.name}\n\nSelect item:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode=None,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_specials_otp_pg:"))
async def seller_specials_otp_pg(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    page = int(parts[1])
    sort_key = parts[2] if len(parts) > 2 else "price_asc"
    await _render_otp_list(callback, session, page=page, sort_key=sort_key)
    await callback.answer()


@router.callback_query(F.data.startswith("seller_specials_logs_pg:"))
async def seller_specials_logs_pg(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    page = int(parts[1])
    sort_key = parts[2] if len(parts) > 2 else "price_asc"
    price_filter = parts[3] if len(parts) > 3 else "all"
    await _render_logs_list(callback, session, page=page, sort_key=sort_key, price_filter=price_filter)
    await callback.answer()


@router.callback_query(F.data.startswith("seller_specials_checks_type:"))
async def seller_specials_checks_type(callback: CallbackQuery, session: AsyncSession):
    raw = callback.data.split(":")
    raw_check_type = raw[1].strip().lower() if len(raw) > 1 else "all"
    page = int(raw[2]) if len(raw) > 2 else 0
    sort_key = raw[3] if len(raw) > 3 else "price_asc"
    stmt = (
        select(SellerCheckItem)
        .join(Seller)
        .where(
            SellerCheckItem.moderation_status == "approved",
            SellerCheckItem.is_active == True,
            SellerCheckItem.is_in_stock == True,
            Seller.is_approved == True,
            Seller.is_active == True,
        )
    )
    if raw_check_type != "all":
        stmt = stmt.where(SellerCheckItem.check_type == raw_check_type)
    items = list((await session.execute(stmt)).scalars().all())
    items = _price_sort(items, sort_key, lambda x: float(_item_price(x)))
    per_page = 10
    total_pages = max(1, (len(items) + per_page - 1) // per_page)
    page = clamp_page(page, len(items), per_page)
    chunk = items[page * per_page : page * per_page + per_page]
    label = "All checks" if raw_check_type == "all" else _format_check_type_label(raw_check_type)
    rows = [
        [
            InlineKeyboardButton(
                text=f"{_item_title(item)} | ${float(_item_price(item)):.2f}",
                callback_data=f"seller_specials_detail:checks:{item.id}",
            )
        ]
        for item in chunk
    ]
    if not rows:
        rows.append([InlineKeyboardButton(text="No items available", callback_data="seller_specials_list:checks")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="⬅️ Prev",
            callback_data=f"seller_specials_checks_type:{raw_check_type}:{page - 1}:{sort_key}",
        ))
    nav.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="page_info"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            text="Next ➡️",
            callback_data=f"seller_specials_checks_type:{raw_check_type}:{page + 1}:{sort_key}",
        ))
    if nav:
        rows.append(nav)
    sort_next = "price_desc" if sort_key == "price_asc" else "price_asc"
    rows.append([
        InlineKeyboardButton(
            text="💲 Price ↑" if sort_key == "price_asc" else "💲 Price ↓",
            callback_data=f"seller_specials_checks_type:{raw_check_type}:0:{sort_next}",
        ),
    ])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="seller_specials_list:checks")])
    await safe_edit_message(
        callback,
        f"📄 Checks\n\nType: {label}\n\nSelect item:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode=None,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_specials_detail:"))
async def seller_specials_detail(callback: CallbackQuery, session: AsyncSession):
    _, raw_kind, item_id_raw = callback.data.split(":")
    kind = _normalize_kind(raw_kind)
    meta = SPECIALS.get(kind)
    if not meta:
        await callback.answer("Unknown category", show_alert=True)
        return
    item = await session.scalar(select(meta["model"]).where(meta["model"].id == int(item_id_raw)))
    if not item:
        await callback.answer("Item not found", show_alert=True)
        return
    detail_rows = []
    if meta.get("chat_before_purchase"):
        detail_rows.append([InlineKeyboardButton(
            text="💬 Ask Seller",
            callback_data=f"seller_specials_pre_chat:{kind}:{item.id}:{item.seller_id}",
        )])
    detail_rows += [
        [InlineKeyboardButton(text="🛒 Buy", callback_data=f"seller_specials_buy:{kind}:{item.id}")],
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"seller_specials_list:{kind}")],
    ]
    await safe_edit_message(
        callback,
        f"{meta['label']}\n\n{_describe_item(kind, item)}\n\nPrice: ${float(_item_price(item)):.2f}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=detail_rows),
        parse_mode=_parse_mode_for_kind(kind),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_specials_buy:"))
async def seller_specials_buy(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int):
    _, raw_kind, item_id_raw = callback.data.split(":")
    kind = _normalize_kind(raw_kind)
    meta = SPECIALS.get(kind)
    if not meta:
        await callback.answer("Unknown category", show_alert=True)
        return
    item = await session.scalar(select(meta["model"]).where(meta["model"].id == int(item_id_raw)))
    if not item or not item.is_in_stock:
        await callback.answer("Item unavailable", show_alert=True)
        return
    price = _item_price(item)
    text = f"⚠️ Confirm purchase?\n\n{_describe_item(kind, item)}\n\n💵 ${float(price):.2f} will be deducted."
    await state.update_data(
        checkout_category="seller_specials",
        checkout_service_name=kind,
        checkout_base_price=str(price),
        checkout_confirm_text=text,
        checkout_keyboard_type="custom",
        checkout_confirm_callback=f"seller_specials_buy_confirm:{kind}:{item.id}",
        checkout_cancel_callback=f"seller_specials_detail:{kind}:{item.id}",
        checkout_parse_mode=_parse_mode_for_kind(kind),
        selected_coupon_code=None,
        selected_user_coupon_id=None,
    )
    await state.set_state(OrderStates.confirmation)
    await safe_edit_message(
        callback,
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Confirm", callback_data=f"seller_specials_buy_confirm:{kind}:{item.id}")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data=f"seller_specials_detail:{kind}:{item.id}")],
        ]),
        parse_mode=_parse_mode_for_kind(kind),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_specials_buy_confirm:"))
async def seller_specials_buy_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int):
    _, raw_kind, item_id_raw = callback.data.split(":")
    kind = _normalize_kind(raw_kind)
    meta = SPECIALS.get(kind)
    if not meta:
        await callback.answer("Unknown category", show_alert=True)
        return
    item = await session.scalar(select(meta["model"]).where(meta["model"].id == int(item_id_raw)))
    if not item or not item.is_in_stock:
        await callback.answer("Item unavailable", show_alert=True)
        return
    price = _item_price(item)
    buyer = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    if buyer is None:
        await callback.answer("User not found", show_alert=True)
        return
    state_data = await state.get_data()
    pricing = await CheckoutCouponService.get_checkout_pricing(
        session,
        telegram_user_id=callback.from_user.id,
        state_data={
            "checkout_category": "seller_specials",
            "checkout_service_name": kind,
            "checkout_base_price": str(price),
            "selected_coupon_code": state_data.get("selected_coupon_code"),
        },
    )
    success = await OrderService.charge_balance(
        session,
        callback.from_user.id,
        pricing.final_amount,
        description=f"{kind} purchase #{item.id}",
        commit=False,
    )
    if not success:
        await callback.answer("Insufficient balance", show_alert=True)
        return

    now = datetime.now(timezone.utc)
    item.is_in_stock = False
    if meta["schema"] == "legacy":
        order = meta["order_model"](
            item_id=item.id,
            buyer_id=buyer.id,
            seller_id=item.seller_id,
            price=float(pricing.final_amount),
            purchased_at=now,
            guarantee_until=now + timedelta(minutes=meta["window"]),
            delivered_at=now,
        )
    else:
        use_reveal = meta.get("use_reveal", False)
        order_kwargs = dict(
            seller_id=item.seller_id,
            buyer_user_id=callback.from_user.id,
            mirror_bot_id=mirror_bot_id,
            status="completed",
            price_for_buyer=pricing.final_amount,
            price_for_seller=getattr(item, "base_price", None) or getattr(item, "seller_price", None) or price,
            result_data={"text": _build_result_text(kind, item)},
            check_window_minutes=meta["window"],
            completed_at=now,
            auto_complete_at=now + timedelta(hours=24) if use_reveal else now + timedelta(minutes=meta["window"]),
        )
        if not use_reveal:
            order_kwargs["check_started_at"] = now
            order_kwargs["check_expires_at"] = now + timedelta(minutes=meta["window"])
        if kind == "nfc":
            order_kwargs["seller_nfc_item_id"] = item.id
            order_kwargs["product_type"] = "nfc"
            order_kwargs["product_subtype"] = item.product_subtype
            order_kwargs["files"] = [item.data_file_path]
        elif kind == "otp":
            order_kwargs["seller_otp_item_id"] = item.id
            order_kwargs["product_type"] = "otp"
            order_kwargs["product_subtype"] = item.product_subtype
        elif kind == "selfreg_cc":
            order_kwargs["seller_selfreg_cc_item_id"] = item.id
            order_kwargs["product_type"] = "bank"
            order_kwargs["product_subtype"] = "selfreg_cc"
        else:
            order_kwargs["seller_check_item_id"] = item.id
            order_kwargs["product_type"] = "bank"
            order_kwargs["product_subtype"] = "checks"
            order_kwargs["files"] = [item.scan_file_path] + ([item.template_file_path] if item.template_file_path else [])
        order = meta["order_model"](**order_kwargs)

    session.add(order)
    await session.commit()
    await state.clear()

    NocoDBService.log_financial_operation(
        user_id=callback.from_user.id,
        amount=pricing.final_amount,
        payment_method="balance",
        tx_id=f"seller_special_purchase:{kind}:{order.id}",
        operation_type="seller_special_purchase",
        extra={
            "kind": kind,
            "item_id": item.id,
            "order_id": order.id,
            "coupon_code": pricing.code,
            "discount_amount": float(pricing.discount_amount),
        },
    )
    if pricing.applied:
        NocoDBService.log_event(
            event_type="coupon_applied",
            actor_type="buyer",
            actor_id=callback.from_user.id,
            target_type="seller_special_order",
            target_id=order.id,
            status="applied",
            payload={
                "coupon_code": pricing.code,
                "category": "seller_specials",
                "service_name": kind,
                "original_amount": float(pricing.original_amount),
                "discount_amount": float(pricing.discount_amount),
                "final_amount": float(pricing.final_amount),
            },
            timestamp=now,
        )
    NocoDBService.log_file_operation(
        user_id=callback.from_user.id,
        action="sell",
        file_id=item.id,
        category="seller_specials",
        extra={"kind": kind, "item_id": item.id, "order_id": order.id},
    )

    if meta.get("use_reveal", False):
        reveal_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Open Product", callback_data=f"special_reveal:{kind}:{order.id}")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="back_main")],
        ])
        await safe_edit_message(
            callback,
            f"✅ Purchase successful!\n\n"
            f"{_describe_item(kind, item)}\n\n"
            f"⚠️ Press the button below to open your product.\n"
            f"You will have {format_guarantee_window(meta['window'])} to verify.\n"
            f"After that, payment is finalized to the seller.",
            reply_markup=reveal_kb,
            parse_mode=_parse_mode_for_kind(kind),
        )
    else:
        text = (
            f"✅ Purchase successful!\n\n"
            f"{_describe_item(kind, item)}\n\n"
            f"⏱ You have {format_guarantee_window(meta['window'])} to verify.\n"
            f"📹 Refund requires video proof within 1 day.\n\n"
            f"{_build_result_text(kind, item)}"
        )
        allow_chat = meta.get("allow_chat", True)
        await safe_edit_message(
            callback,
            text,
            reply_markup=_special_result_keyboard(kind, order.id, allow_chat=allow_chat),
            parse_mode=_parse_mode_for_kind(kind),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_specials_feedback:"))
async def seller_specials_feedback(callback: CallbackQuery, session: AsyncSession):
    _, raw_kind, order_id_raw, status = callback.data.split(":")
    kind = _normalize_kind(raw_kind)
    meta = SPECIALS.get(kind)
    if not meta:
        await callback.answer("Unknown category", show_alert=True)
        return
    order = await session.scalar(select(meta["order_model"]).where(meta["order_model"].id == int(order_id_raw)))
    buyer = await session.scalar(select(User).where(User.user_id == callback.from_user.id))
    if not _order_belongs_to_user(order, buyer):
        await callback.answer("Order not found", show_alert=True)
        return
    if hasattr(order, "feedback_status"):
        order.feedback_status = status
    if hasattr(order, "feedback_at"):
        order.feedback_at = datetime.now(timezone.utc)
    if hasattr(order, "rating"):
        order.rating = 1 if status == "liked" else 0
    seller = await session.scalar(select(Seller).where(Seller.id == order.seller_id))
    if seller:
        if status == "liked":
            seller.likes_count = int(seller.likes_count or 0) + 1
        else:
            seller.dislikes_count = int(seller.dislikes_count or 0) + 1
    await session.commit()
    await safe_edit_message(
        callback,
        "Feedback saved.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data="seller_specials_main")]]),
        parse_mode=None,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_specials_report:"))
async def seller_specials_report(callback: CallbackQuery, session: AsyncSession):
    _, raw_kind, order_id_raw = callback.data.split(":")
    kind = _normalize_kind(raw_kind)
    meta = SPECIALS.get(kind)
    if not meta:
        await callback.answer("Unknown category", show_alert=True)
        return
    order = await session.scalar(select(meta["order_model"]).where(meta["order_model"].id == int(order_id_raw)))
    buyer = await session.scalar(select(User).where(User.user_id == callback.from_user.id))
    if not _order_belongs_to_user(order, buyer):
        await callback.answer("Order not found", show_alert=True)
        return
    if not is_guarantee_active(_order_guarantee_until(order)):
        await callback.answer("Guarantee window expired", show_alert=True)
        return
    order.report_status = "reported"
    if hasattr(order, "reported_at"):
        order.reported_at = datetime.now(timezone.utc)
    conv = await get_or_create_conversation(
        session,
        seller_id=order.seller_id,
        buyer_user_id=callback.from_user.id,
        mirror_bot_id=getattr(order, "mirror_bot_id", None),
        source_order_type=kind,
        source_order_id=order.id,
    )
    await session.commit()
    await safe_edit_message(
        callback,
        (
            "📹 Refund Request\n\n"
            "Video proof is required (within 1 day).\n\n"
            "We recommend asking the seller directly first — "
            "most issues are resolved quickly that way."
        ),
        reply_markup=_special_refund_options_keyboard(kind, order.id, conv.id),
        parse_mode=None,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_specials_moderation:"))
async def seller_specials_moderation(callback: CallbackQuery, session: AsyncSession):
    """Buyer requests moderation (skips seller chat)."""
    _, raw_kind, order_id_raw = callback.data.split(":")
    kind = _normalize_kind(raw_kind)
    meta = SPECIALS.get(kind)
    if not meta:
        await callback.answer("Unknown category", show_alert=True)
        return
    order = await session.scalar(select(meta["order_model"]).where(meta["order_model"].id == int(order_id_raw)))
    buyer = await session.scalar(select(User).where(User.user_id == callback.from_user.id))
    if not _order_belongs_to_user(order, buyer):
        await callback.answer("Order not found", show_alert=True)
        return
    if hasattr(order, "report_status"):
        order.report_status = "moderation_requested"
    if hasattr(order, "reported_at"):
        order.reported_at = datetime.now(timezone.utc)
    await session.commit()
    try:
        from shared.services.admin_notification_service import AdminNotificationService
        await AdminNotificationService.notify_new_dispute(
            order_type=kind,
            order_id=order.id,
            buyer_user_id=callback.from_user.id,
            seller_id=order.seller_id,
        )
    except Exception:
        pass
    await safe_edit_message(
        callback,
        (
            "✅ Moderation request submitted.\n\n"
            "📹 Please prepare video proof — moderator will contact you shortly.\n"
            "You will receive a notification when a decision is made."
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")],
        ]),
        parse_mode=None,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_specials_pre_chat:"))
async def seller_specials_pre_chat(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int):
    """Ask Seller before purchase — opens conversation."""
    _, raw_kind, item_id_raw, seller_id_raw = callback.data.split(":")
    kind = _normalize_kind(raw_kind)
    conv = await get_or_create_conversation(
        session,
        seller_id=int(seller_id_raw),
        buyer_user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
        source_order_type=kind,
        source_order_id=None,
    )
    await session.commit()
    await safe_edit_message(
        callback,
        "💬 Chat opened. You can ask the seller any questions before purchasing.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Open Chat", callback_data=f"buyer_chat_conv:{conv.id}:0")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data=f"seller_specials_detail:{kind}:{item_id_raw}")],
        ]),
        parse_mode=None,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_specials_ask_seller:"))
async def seller_specials_ask_seller(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int):
    """Ask Seller after purchase — opens existing conversation."""
    _, raw_kind, order_id_raw = callback.data.split(":")
    kind = _normalize_kind(raw_kind)
    meta = SPECIALS.get(kind)
    if not meta:
        await callback.answer("Unknown category", show_alert=True)
        return
    order = await session.scalar(select(meta["order_model"]).where(meta["order_model"].id == int(order_id_raw)))
    buyer = await session.scalar(select(User).where(User.user_id == callback.from_user.id))
    if not _order_belongs_to_user(order, buyer):
        await callback.answer("Order not found", show_alert=True)
        return
    conv = await get_or_create_conversation(
        session,
        seller_id=order.seller_id,
        buyer_user_id=callback.from_user.id,
        mirror_bot_id=getattr(order, "mirror_bot_id", None),
        source_order_type=kind,
        source_order_id=order.id,
    )
    await session.commit()
    await safe_edit_message(
        callback,
        "💬 Open chat with seller:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Open Chat", callback_data=f"buyer_chat_conv:{conv.id}:{order.id}")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="seller_specials_main")],
        ]),
        parse_mode=None,
    )
    await callback.answer()


# ============================================
# REVEAL FLOW for NFC / OTP / Enroll
# ============================================

@router.callback_query(F.data.startswith("special_reveal:"))
async def special_reveal_handler(callback: CallbackQuery, session: AsyncSession):
    """Buyer opens the product — starts the guarantee timer."""
    parts = callback.data.split(":")
    raw_kind = parts[1]
    order_id = int(parts[2])
    kind = _normalize_kind(raw_kind)
    meta = SPECIALS.get(kind)
    if not meta:
        await callback.answer("Unknown category", show_alert=True)
        return
    order = await session.scalar(select(meta["order_model"]).where(meta["order_model"].id == order_id))
    buyer = await session.scalar(select(User).where(User.user_id == callback.from_user.id))
    if not _order_belongs_to_user(order, buyer):
        await callback.answer("Order not found", show_alert=True)
        return

    now = datetime.now(timezone.utc)
    if not order.check_started_at:
        order.check_started_at = now
        order.check_expires_at = now + timedelta(minutes=meta["window"])
        order.auto_complete_at = order.check_expires_at
        await session.commit()

    product_text = (order.result_data or {}).get("text", "No data")
    allow_chat = meta.get("allow_chat", True)

    await safe_edit_message(
        callback,
        f"🔐 {meta['label']} Order #{order.id}\n\n"
        f"⏱ You have {format_guarantee_window(meta['window'])} to verify.\n"
        f"After that, payment goes to the seller.\n\n"
        f"🔑 Your product:\n{product_text}",
        reply_markup=_special_result_keyboard(kind, order.id, allow_chat=allow_chat),
        parse_mode=_parse_mode_for_kind(kind),
    )
    await callback.answer()


@router.callback_query(F.data == "page_info")
async def page_info_noop_handler(callback: CallbackQuery):
    """No-op handler for page navigation indicator buttons (P1-1 fix)"""
    await callback.answer()


# ── End of file ────────────────────────────────────────────────────────────

