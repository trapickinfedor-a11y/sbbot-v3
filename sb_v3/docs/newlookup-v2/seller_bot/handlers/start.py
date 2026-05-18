from __future__ import annotations

import logging
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select

from seller_bot.constants.language_loader import get_buttons, get_texts
from seller_bot.keyboards.inline import (
    seller_main_menu,
    admin_approval_keyboard,
    language_keyboard,
    rules_accept_keyboard,
)
from seller_bot.handlers.helpers import render_pending_helper_invite
from seller_bot.services.seller_service import SellerService
from seller_bot.utils import get_seller_unread_count
from seller_bot.config import seller_bot_config
from shared.database.models import SellerDepositPayment
from shared.i18n import t
from shared.services.btcpay_service import BTCPayService
from shared.services.seller_deposit_service import SellerDepositService

logger = logging.getLogger(__name__)
router = Router(name="seller_start")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Global /cancel — clears any active FSM state."""
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer("❌ Cancelled.")
    else:
        await message.answer("Nothing to cancel.")


async def _notify_admins_about_application(bot: Bot, seller, from_user) -> None:
    for admin_id in seller_bot_config.admin_ids:
        try:
            await bot.send_message(
                admin_id,
                f"🆕 <b>New Seller Application</b>\n\n"
                f"👤 Name: {from_user.full_name}\n"
                f"📱 Username: @{from_user.username or 'N/A'}\n"
                f"🆔 Telegram ID: <code>{from_user.id}</code>\n"
                f"📋 Seller ID: {seller.id}\n"
                f"🌍 Language: {seller.language}\n"
                f"✅ Rules accepted: {'yes' if seller.rules_accepted else 'no'}",
                reply_markup=admin_approval_keyboard(seller.id)
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")


def _deposit_keyboard(checkout_url: str = None, lang: str = "en") -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🏦 Pay Bank package ($100)", callback_data="seller_deposit_package:bank")],
        [InlineKeyboardButton(text="💳 Pay CC package ($50)", callback_data="seller_deposit_package:cc")],
        [InlineKeyboardButton(text="🏦➕ Pay Bank Plus ($150)", callback_data="seller_deposit_package:bank_plus")],
        [InlineKeyboardButton(text="💳➕ Pay CC Plus ($100)", callback_data="seller_deposit_package:cc_plus")],
        [InlineKeyboardButton(text="🎯 Pay Full package ($250)", callback_data="seller_deposit_package:full")],
    ]
    if checkout_url:
        rows.append([InlineKeyboardButton(text="💸 Open BTCPay Invoice", url=checkout_url)])
        rows.append([InlineKeyboardButton(text="🔄 Check payment", callback_data="seller_deposit_check")])
    rows.append([InlineKeyboardButton(text="↩️ Back", callback_data="seller_deposit_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _deposit_text(seller, lang: str = "en") -> str:
    return t("seller.deposit_info", lang)


def _service_info_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    """Shown after language selection — Read more / Continue to deposit."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✅ Continue",
            callback_data="seller_rules_accept",
        )],
    ])


@router.message(CommandStart())
async def start_handler(message: Message, session: AsyncSession, is_seller: bool, seller, texts, buttons, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    # Admin without seller record — auto-create approved seller for full access
    is_admin = kwargs.get("is_admin", False)
    if is_admin and not seller:
        seller = await SellerService.get_or_create_admin_seller(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            display_name=message.from_user.full_name
        )
    
    if seller_actor and seller_actor.is_helper and seller_actor.pending_approval:
        rendered = await render_pending_helper_invite(message, seller_actor, buttons=buttons)
        if rendered:
            return

    if is_seller and seller:
        unread = await get_seller_unread_count(session, seller.id)
        await message.answer(
            texts.WELCOME_BACK.format(
                name=seller.display_name,
                total_orders=seller.total_orders,
                total_earned=seller.total_earned,
            ),
            reply_markup=seller_main_menu(
                unread_count=unread,
                buttons=buttons,
                actor_role=seller_actor.role if seller_actor else None,
            )
        )
        return
    
    if seller and not seller.rules_accepted:
        seller_texts = get_texts(seller.language or "en")
        seller_buttons = get_buttons(seller.language or "en")
        await message.answer(
            seller_texts.RULES_TEXT,
            reply_markup=rules_accept_keyboard(seller_buttons)
        )
        return

    pending = kwargs.get("pending_approval", False)
    if pending and seller:
        lang = getattr(seller, "language", None) or "en"
        await message.answer(_deposit_text(seller, lang), reply_markup=_deposit_keyboard(lang=lang))
        return
    
    await message.answer(
        texts.CHOOSE_LANGUAGE,
        reply_markup=language_keyboard()
    )


@router.message(Command("register"))
async def register_handler(message: Message, session: AsyncSession, is_seller: bool, seller, texts, buttons, **kwargs):
    if is_seller and seller:
        await message.answer(texts.ALREADY_REGISTERED)
        return
    
    if seller and not seller.rules_accepted:
        seller_texts = get_texts(seller.language or "en")
        seller_buttons = get_buttons(seller.language or "en")
        await message.answer(
            seller_texts.RULES_TEXT,
            reply_markup=rules_accept_keyboard(seller_buttons)
        )
        return

    if seller and not SellerDepositService.seller_is_active(seller):
        lang = getattr(seller, "language", None) or "en"
        await message.answer(_deposit_text(seller, lang), reply_markup=_deposit_keyboard(lang=lang))
        return
    
    await message.answer(
        texts.CHOOSE_LANGUAGE,
        reply_markup=language_keyboard()
    )


@router.callback_query(F.data == "seller_menu")
async def menu_callback(callback: CallbackQuery, session: AsyncSession, is_seller: bool, seller, texts, buttons, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    if not is_seller or not seller:
        await callback.answer(texts.NO_SELLER_ACCESS, show_alert=True)
        return
    
    unread = await get_seller_unread_count(session, seller.id)
    await callback.message.edit_text(
        texts.MENU_TEXT.format(
            name=seller.display_name,
            total_orders=seller.total_orders,
            total_earned=seller.total_earned,
        ),
        reply_markup=seller_main_menu(
            unread_count=unread,
            buttons=buttons,
            actor_role=seller_actor.role if seller_actor else None,
        )
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_lang:"))
async def seller_choose_language(callback: CallbackQuery, session: AsyncSession, seller, **kwargs):
    language = callback.data.split(":", 1)[1].strip().lower()
    if language not in {"en", "ru", "zh", "es"}:
        await callback.answer("Unsupported language", show_alert=True)
        return

    chosen_texts = get_texts(language)
    draft_seller = await SellerService.create_or_update_seller_draft(
        session,
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        display_name=callback.from_user.full_name,
        language=language,
    )

    if draft_seller.is_approved and draft_seller.is_active:
        chosen_buttons = get_buttons(language)
        unread = await get_seller_unread_count(session, draft_seller.id)
        await callback.message.edit_text(
            chosen_texts.WELCOME_BACK.format(
                name=draft_seller.display_name,
                total_orders=draft_seller.total_orders,
                total_earned=draft_seller.total_earned,
            ),
            reply_markup=seller_main_menu(unread_count=unread, buttons=chosen_buttons, actor_role="owner")
        )
        await callback.answer()
        return

    # Show service info / onboarding description before rules
    service_info = t("seller.onboarding_service_info", language)
    await callback.message.edit_text(
        service_info,
        reply_markup=_service_info_keyboard(language),
    )
    await callback.answer()


@router.callback_query(F.data == "seller_rules_accept")
async def seller_accept_rules(callback: CallbackQuery, session: AsyncSession, seller, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    existing_seller = seller or await SellerService.get_seller(session, callback.from_user.id)
    if existing_seller and existing_seller.is_approved and existing_seller.is_active:
        lang = getattr(existing_seller, "language", None) or "en"
        seller_texts = get_texts(lang)
        seller_buttons = get_buttons(lang)
        unread = await get_seller_unread_count(session, existing_seller.id)
        await callback.message.edit_text(
            seller_texts.WELCOME_BACK.format(
                name=existing_seller.display_name,
                total_orders=existing_seller.total_orders,
                total_earned=existing_seller.total_earned,
            ),
            reply_markup=seller_main_menu(
                unread_count=unread,
                buttons=seller_buttons,
                actor_role=seller_actor.role if seller_actor else "owner",
            )
        )
        await callback.answer()
        return

    if existing_seller and existing_seller.rules_accepted:
        lang = getattr(existing_seller, "language", None) or "en"
        if SellerDepositService.seller_is_active(existing_seller):
            seller_texts = get_texts(lang)
            seller_buttons = get_buttons(lang)
            unread = await get_seller_unread_count(session, existing_seller.id)
            await callback.message.edit_text(
                seller_texts.WELCOME_BACK.format(
                    name=existing_seller.display_name,
                    total_orders=existing_seller.total_orders,
                    total_earned=existing_seller.total_earned,
                ),
                reply_markup=seller_main_menu(
                    unread_count=unread,
                    buttons=seller_buttons,
                    actor_role=seller_actor.role if seller_actor else "owner",
                )
            )
        else:
            await callback.message.edit_text(
                _deposit_text(existing_seller, lang),
                reply_markup=_deposit_keyboard(lang=lang),
            )
        await callback.answer()
        return

    language = (existing_seller.language if existing_seller else None) or "en"
    # Show rules first
    seller_texts = get_texts(language)
    seller_buttons = get_buttons(language)
    # Register (mark as accepted when they proceed through rules)
    new_seller = await SellerService.register_seller(
        session,
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        display_name=callback.from_user.full_name,
        language=language,
        rules_accepted=True,
    )
    await callback.message.edit_text(
        _deposit_text(new_seller, language),
        reply_markup=_deposit_keyboard(lang=language),
    )
    await callback.answer("Application submitted")


@router.callback_query(F.data == "seller_rules_decline")
async def seller_decline_rules(callback: CallbackQuery, session: AsyncSession, seller, texts, **kwargs):
    existing_seller = seller or await SellerService.get_seller(session, callback.from_user.id)
    if existing_seller:
        existing_seller.rules_accepted = False
        await session.commit()
    await callback.message.edit_text(
        texts.RULES_DECLINED,
        reply_markup=language_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "seller_deposit_back")
async def seller_deposit_back(callback: CallbackQuery, session: AsyncSession, **kwargs):
    seller = await SellerService.get_seller(session, callback.from_user.id)
    if not seller:
        await callback.answer("Seller not found", show_alert=True)
        return
    lang = getattr(seller, "language", None) or "en"
    await callback.message.edit_text(
        _deposit_text(seller, lang),
        reply_markup=_deposit_keyboard(lang=lang),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_deposit_package:"))
async def seller_deposit_package(callback: CallbackQuery, session: AsyncSession, **kwargs):
    seller = await SellerService.get_seller(session, callback.from_user.id)
    if not seller:
        await callback.answer("Seller not found", show_alert=True)
        return
    lang = getattr(seller, "language", None) or "en"
    package_code = callback.data.split(":", 1)[1]
    if package_code in SellerDepositService.allowed_categories(seller):
        await callback.answer("This package is already active.", show_alert=True)
        return
    if not BTCPayService.is_configured():
        await callback.answer("BTCPay is not configured yet.", show_alert=True)
        return
    try:
        payment = await SellerDepositService.create_btcpay_invoice(session, seller, package_code)
    except Exception as exc:
        logger.error("Failed to create BTCPay invoice: %s", exc)
        await callback.answer("Failed to create invoice. Try again later.", show_alert=True)
        return
    await callback.message.edit_text(
        _deposit_text(seller, lang) + f"\n\nSelected package: <b>{SellerDepositService.package_label(package_code)}</b>",
        reply_markup=_deposit_keyboard(payment.checkout_url, lang=lang),
    )
    await callback.answer("Invoice created")


@router.callback_query(F.data == "seller_deposit_check")
async def seller_deposit_check(callback: CallbackQuery, session: AsyncSession, **kwargs):
    seller = await SellerService.get_seller(session, callback.from_user.id)
    if not seller:
        await callback.answer("Seller not found", show_alert=True)
        return
    payment = await session.scalar(
        select(SellerDepositPayment)
        .where(SellerDepositPayment.seller_id == seller.id)
        .order_by(desc(SellerDepositPayment.created_at))
    )
    if not payment or not payment.provider_invoice_id:
        await callback.answer("No recent deposit invoice found.", show_alert=True)
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
        seller_texts = get_texts(seller.language or "en")
        seller_buttons = get_buttons(seller.language or "en")
        unread = await get_seller_unread_count(session, seller.id)
        await callback.message.edit_text(
            seller_texts.APPLICATION_APPROVED,
            reply_markup=seller_main_menu(unread_count=unread, buttons=seller_buttons, actor_role="owner")
        )
        await callback.answer("Payment confirmed", show_alert=True)
        return

    await callback.answer(f"Payment status: {status or 'pending'}", show_alert=True)


@router.callback_query(F.data.startswith("admin_approve_seller:"))
async def admin_approve_seller(callback: CallbackQuery, session: AsyncSession, is_admin: bool, **kwargs):
    if not is_admin:
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    seller_id = int(callback.data.split(":")[1])
    seller = await SellerService.approve_seller(session, seller_id)
    
    if not seller:
        await callback.answer("Seller not found", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"✅ <b>Seller Approved</b>\n\n"
        f"👤 {seller.display_name}\n"
        f"🆔 ID: {seller.id}\n"
        f"📱 @{seller.username or 'N/A'}"
    )
    
    # Notify the seller
    try:
        seller_texts = get_texts(seller.language or "en")
        seller_buttons = get_buttons(seller.language or "en")
        unread = await get_seller_unread_count(session, seller.id)
        await callback.bot.send_message(
            seller.telegram_id,
            seller_texts.APPLICATION_APPROVED,
            reply_markup=seller_main_menu(unread_count=unread, buttons=seller_buttons, actor_role="owner")
        )
    except Exception as e:
        logger.error(f"Failed to notify seller {seller.telegram_id}: {e}")
    
    await callback.answer("✅ Seller approved!")


@router.callback_query(F.data.startswith("admin_reject_seller:"))
async def admin_reject_seller(callback: CallbackQuery, session: AsyncSession, is_admin: bool, **kwargs):
    if not is_admin:
        await callback.answer("❌ Admin only", show_alert=True)
        return
    
    seller_id = int(callback.data.split(":")[1])
    seller = await SellerService.reject_seller(session, seller_id)
    
    if not seller:
        await callback.answer("Seller not found", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"❌ <b>Seller Rejected</b>\n\n"
        f"👤 {seller.display_name}\n"
        f"🆔 ID: {seller.id}"
    )
    
    try:
        await callback.bot.send_message(
            seller.telegram_id,
            "❌ <b>Your seller application was rejected.</b>\n\n"
            "Contact the admin for more information."
        )
    except Exception as e:
        logger.error(f"Failed to notify seller {seller.telegram_id}: {e}")
    
    await callback.answer("❌ Seller rejected")
