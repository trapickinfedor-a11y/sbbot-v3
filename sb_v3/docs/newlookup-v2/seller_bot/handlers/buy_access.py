"""seller_bot/handlers/buy_access.py

Allows an active seller to purchase access to additional product categories
by paying an extra security deposit via BTCPay.

Flow:
1. Seller presses "Buy Access" button  → show package menu with current access info
2. Seller selects a package            → create BTCPay invoice, show checkout link
3. Seller presses "Check payment"      → verify invoice status and unlock categories

Python 3.9-compatible (no walrus, no match/case, no X | Y union types).
"""
from __future__ import annotations

import logging
from typing import Optional

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from seller_bot.services.seller_service import SellerService
from shared.database.models import SellerDepositPayment
from shared.i18n import t
from shared.services.btcpay_service import BTCPayService
from shared.services.seller_deposit_service import (
    PACKAGE_AMOUNTS,
    SellerDepositService,
)

logger = logging.getLogger(__name__)
router = Router(name="seller_buy_access")

# Packages available for purchase
_BUY_PACKAGES = [
    ("bank", "btn_bank_pkg"),
    ("cc", "btn_cc_pkg"),
    ("bank_plus", "btn_bank_plus_pkg"),
    ("cc_plus", "btn_cc_plus_pkg"),
    ("full", "btn_full_pkg"),
]


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------

def _buy_access_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    rows = []
    for pkg_code, btn_key in _BUY_PACKAGES:
        label = t(f"seller_buttons.{btn_key}", lang)
        rows.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"seller_buy_access_pkg:{pkg_code}",
            )
        ])
    rows.append([
        InlineKeyboardButton(
            text=t("common.back", lang),
            callback_data="seller_menu",
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _invoice_keyboard(checkout_url: str, lang: str = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Open BTCPay Invoice", url=checkout_url)],
        [InlineKeyboardButton(
            text="🔄 " + t("common.loading", lang),
            callback_data="seller_buy_access_check",
        )],
        [InlineKeyboardButton(
            text=t("common.back", lang),
            callback_data="seller_buy_access",
        )],
    ])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _current_access_label(seller, lang: str) -> str:
    cats = SellerDepositService.allowed_categories(seller)
    if not cats:
        return "none"
    return ", ".join(sorted(cats))


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "seller_buy_access")
async def buy_access_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    is_seller: bool,
    seller,
    **kwargs,
) -> None:
    if not is_seller or not seller:
        await callback.answer(t("seller.no_access"), show_alert=True)
        return

    lang = getattr(seller, "language", None) or "en"
    current = _current_access_label(seller, lang)

    await callback.message.edit_text(
        t("seller.buy_access_menu", lang, current_access=current),
        reply_markup=_buy_access_keyboard(lang),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_buy_access_pkg:"))
async def buy_access_select_package(
    callback: CallbackQuery,
    session: AsyncSession,
    is_seller: bool,
    seller,
    **kwargs,
) -> None:
    if not is_seller or not seller:
        await callback.answer(t("seller.no_access"), show_alert=True)
        return

    lang = getattr(seller, "language", None) or "en"
    pkg_code = callback.data.split(":", 1)[1]

    # Validate package code
    if pkg_code not in PACKAGE_AMOUNTS:
        await callback.answer("Invalid package", show_alert=True)
        return

    # Check if all cats already unlocked
    pkg_cats = SellerDepositService.package_categories(pkg_code)
    current_cats = SellerDepositService.allowed_categories(seller)
    if pkg_cats.issubset(current_cats):
        await callback.answer(t("seller.buy_access_already_have", lang), show_alert=True)
        return

    if not BTCPayService.is_configured():
        await callback.answer(t("seller.buy_access_no_btcpay", lang), show_alert=True)
        return

    try:
        payment = await SellerDepositService.create_btcpay_invoice(
            session, seller, pkg_code
        )
    except Exception as exc:
        logger.error("Failed to create BTCPay invoice for buy_access: %s", exc)
        await callback.answer("Failed to create invoice. Try again later.", show_alert=True)
        return

    pkg_label = SellerDepositService.package_label(pkg_code)
    amount_str = str(PACKAGE_AMOUNTS.get(pkg_code, "?"))
    await callback.message.edit_text(
        t(
            "seller.buy_access_invoice_created",
            lang,
            package_label=pkg_label,
            amount=amount_str,
        ),
        reply_markup=_invoice_keyboard(payment.checkout_url, lang),
    )
    await callback.answer("Invoice created")


@router.callback_query(F.data == "seller_buy_access_check")
async def buy_access_check_payment(
    callback: CallbackQuery,
    session: AsyncSession,
    is_seller: bool,
    seller,
    **kwargs,
) -> None:
    if not is_seller or not seller:
        await callback.answer(t("seller.no_access"), show_alert=True)
        return

    lang = getattr(seller, "language", None) or "en"

    # Find most recent pending payment
    payment = await session.scalar(
        select(SellerDepositPayment)
        .where(
            SellerDepositPayment.seller_id == seller.id,
            SellerDepositPayment.status == "pending",
        )
        .order_by(desc(SellerDepositPayment.created_at))
    )
    if not payment or not payment.provider_invoice_id:
        await callback.answer("No pending invoice found.", show_alert=True)
        return

    try:
        invoice_payload = await BTCPayService.fetch_invoice(payment.provider_invoice_id)
        status = str(invoice_payload.get("status") or "")
    except Exception as exc:
        logger.error("Failed to check BTCPay invoice: %s", exc)
        await callback.answer("Could not check payment status.", show_alert=True)
        return

    if BTCPayService.is_paid_status(status):
        await SellerDepositService.process_paid_invoice(
            session,
            payment.provider_invoice_id,
            invoice_payload=invoice_payload,
        )
        await session.refresh(seller)
        new_cats = ", ".join(sorted(SellerDepositService.allowed_categories(seller)))
        await callback.message.edit_text(
            t("seller.buy_access_confirmed", lang, categories=new_cats),
        )
        await callback.answer("Payment confirmed!", show_alert=True)
        return

    await callback.answer(f"Payment status: {status or 'pending'}", show_alert=True)
