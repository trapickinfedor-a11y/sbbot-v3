from __future__ import annotations

"""
Education — подписки (заказы на время) и мануалы (каталог файлов).
Subscriptions: создаётся Order, воркер вручную выдаёт доступ.
Manuals: файл доставляется автоматически после оплаты.
"""

import logging
import os
from decimal import Decimal

from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, BufferedInputFile,
    InputMediaPhoto,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import EducationCategory, EducationSubscription, EducationManual, ManualDelivery
from mirror_bot.services.order_service import OrderService
from mirror_bot.services.checkout_coupon_service import CheckoutCouponService
from mirror_bot.services.user_service import UserService
from mirror_bot.constants.service_eta import ServiceETA
from mirror_bot.utils.message_utils import safe_edit_message
from mirror_bot.constants.buttons_en import ButtonTexts
from mirror_bot.utils.media_library import resolve_bot_photo
from mirror_bot.services.menu_counts_service import MenuCountService

logger = logging.getLogger(__name__)
router = Router()

EDUCATION_PHOTO = resolve_bot_photo("education", fallback_path="media/main.jpg")


class EducationStates(StatesGroup):
    confirm_subscription = State()
    confirm_manual = State()


def education_main_keyboard(buttons, counts: dict | None = None) -> InlineKeyboardMarkup:
    """Main Education menu — Subscriptions + Manuals."""
    counts = counts or {}
    sub_text = ButtonTexts.with_count(getattr(buttons, "EDU_SUBSCRIPTIONS", "📅 Subscriptions"), counts.get("subscriptions_total"))
    man_text = ButtonTexts.with_count(getattr(buttons, "EDU_MANUALS", "📖 Manuals"), counts.get("manuals_total"))
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=sub_text, callback_data="education_subscriptions")],
        [InlineKeyboardButton(text=man_text, callback_data="education_manuals")],
        [InlineKeyboardButton(text=getattr(buttons, "BACK", "⬅️ Back"), callback_data="back_main")],
    ])


def _education_confirm_keyboard(confirm_callback: str, cancel_callback: str, buttons=None) -> InlineKeyboardMarkup:
    confirm_text = getattr(buttons, "CONFIRM", "✅ Confirm") if buttons else "✅ Confirm"
    cancel_text = getattr(buttons, "CANCEL", "❌ Cancel") if buttons else "❌ Cancel"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=confirm_text, callback_data=confirm_callback)],
        [InlineKeyboardButton(text=cancel_text, callback_data=cancel_callback)],
    ])


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _load_sub_categories(session: AsyncSession):
    result = await session.execute(
        select(EducationCategory)
        .where(EducationCategory.is_active == True, EducationCategory.item_type == "subscription")
        .order_by(EducationCategory.position)
    )
    return result.scalars().all()


async def _load_man_categories(session: AsyncSession):
    result = await session.execute(
        select(EducationCategory)
        .where(EducationCategory.is_active == True, EducationCategory.item_type == "manual")
        .order_by(EducationCategory.position)
    )
    return result.scalars().all()


async def _load_subscriptions(session: AsyncSession, category_code: str = None):
    q = select(EducationSubscription).where(EducationSubscription.is_active == True)
    if category_code:
        q = q.where(EducationSubscription.category_code == category_code)
    q = q.order_by(EducationSubscription.position)
    result = await session.execute(q)
    return result.scalars().all()


async def _load_manuals(session: AsyncSession, category_code: str = None):
    q = select(EducationManual).where(EducationManual.is_active == True, EducationManual.is_available == True)
    if category_code:
        q = q.where(EducationManual.category_code == category_code)
    q = q.order_by(EducationManual.position)
    result = await session.execute(q)
    return result.scalars().all()


def _sub_categories_keyboard(categories, buttons, counts=None) -> InlineKeyboardMarkup:
    counts = counts or {}
    rows = []
    for cat in categories:
        rows.append([InlineKeyboardButton(text=ButtonTexts.with_count(f"📂 {cat.name}", counts.get(cat.code)), callback_data=f"edu_sub_cat:{cat.code}")])
    rows.append([InlineKeyboardButton(text=getattr(buttons, "EDU_BACK", "⬅️ Back"), callback_data="education_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _man_categories_keyboard(categories, buttons, counts=None) -> InlineKeyboardMarkup:
    counts = counts or {}
    rows = []
    for cat in categories:
        rows.append([InlineKeyboardButton(text=ButtonTexts.with_count(f"📂 {cat.name}", counts.get(cat.code)), callback_data=f"edu_man_cat:{cat.code}")])
    rows.append([InlineKeyboardButton(text=getattr(buttons, "EDU_BACK", "⬅️ Back"), callback_data="education_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _subscriptions_keyboard(items, cat_code, buttons) -> InlineKeyboardMarkup:
    back_text = getattr(buttons, "EDU_BACK", "⬅️ Back")
    rows = []
    for item in items:
        rows.append([InlineKeyboardButton(
            text=f"📅 {item.name} — {item.duration_days}d — ${item.price}",
            callback_data=f"edu_sub:{item.id}"
        )])
    rows.append([InlineKeyboardButton(text=back_text, callback_data=f"edu_sub_cat:{cat_code}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _manuals_keyboard(items, cat_code, buttons) -> InlineKeyboardMarkup:
    back_text = getattr(buttons, "EDU_BACK", "⬅️ Back")
    rows = []
    for item in items:
        rows.append([InlineKeyboardButton(
            text=f"📖 {item.name} — ${item.price}",
            callback_data=f"edu_man:{item.id}"
        )])
    rows.append([InlineKeyboardButton(text=back_text, callback_data=f"edu_man_cat:{cat_code}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─── Main menu ────────────────────────────────────────────────────────────────

@router.message(F.text.in_(ButtonTexts.get_all_variants("EDUCATION")))
async def education_main_handler(message: Message, session: AsyncSession, texts, buttons):
    counts = await MenuCountService.get_education_counts(session)
    try:
        if EDUCATION_PHOTO:
            await message.answer_photo(
                photo=EDUCATION_PHOTO,
                caption=getattr(texts, "EDUCATION_MAIN", "📚 *Education*\n\nSubscriptions — time-based access\nManuals — file catalog"),
                reply_markup=education_main_keyboard(buttons, counts),
                parse_mode="Markdown",
            )
        else:
            raise RuntimeError("Education photo is not configured")
    except Exception as e:
        logger.exception(e)
        await message.answer("📚 Education\n\nSubscriptions | Manuals", reply_markup=education_main_keyboard(buttons, counts))


@router.callback_query(F.data == "education_main")
async def education_main_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession, texts, buttons):
    await state.clear()
    counts = await MenuCountService.get_education_counts(session)
    try:
        await callback.message.delete()
        if EDUCATION_PHOTO:
            await callback.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=EDUCATION_PHOTO,
                caption=getattr(texts, "EDUCATION_MAIN", "📚 *Education*\n\nSubscriptions — time-based access\nManuals — file catalog"),
                reply_markup=education_main_keyboard(buttons, counts),
                parse_mode="Markdown",
            )
        else:
            raise RuntimeError("Education photo is not configured")
    except Exception:
        await safe_edit_message(
            callback,
            getattr(texts, "EDUCATION_MAIN", "📚 *Education*\n\nSubscriptions — time-based access\nManuals — file catalog"),
            reply_markup=education_main_keyboard(buttons, counts),
            parse_mode="Markdown",
        )
    await callback.answer()


# ─── Subscriptions ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "education_subscriptions")
async def education_subscriptions_handler(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    categories = await _load_sub_categories(session)
    counts = await MenuCountService.get_education_counts(session)
    if not categories:
        # Нет категорий — показываем все подписки без категорий
        items = await _load_subscriptions(session)
        if not items:
            await safe_edit_message(
                callback,
                "📅 *Subscriptions*\n\nNo subscriptions available yet. Check back later!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=getattr(buttons, "EDU_BACK", "⬅️ Back"), callback_data="education_main")]
                ]),
                parse_mode="Markdown",
            )
            await callback.answer()
            return

        # Показываем всё в одном списке
        rows = []
        for item in items:
            rows.append([InlineKeyboardButton(
                text=f"📅 {item.name} — {item.duration_days}d — ${item.price}",
                callback_data=f"edu_sub:{item.id}"
            )])
        rows.append([InlineKeyboardButton(text=getattr(buttons, "EDU_BACK", "⬅️ Back"), callback_data="education_main")])
        await safe_edit_message(
            callback,
            "📅 *Subscriptions*\n\nSelect a plan:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
            parse_mode="Markdown",
        )
        await callback.answer()
        return

    await safe_edit_message(
        callback,
        "📅 *Subscriptions*\n\nSelect a category:",
        reply_markup=_sub_categories_keyboard(categories, buttons, counts["subscriptions_by_category"]),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edu_sub_cat:"))
async def edu_sub_category_handler(callback: CallbackQuery, session: AsyncSession, buttons):
    cat_code = callback.data.split(":", 1)[1]
    items = await _load_subscriptions(session, cat_code)

    if not items:
        await safe_edit_message(
            callback,
            "📅 No subscriptions in this category yet.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Back", callback_data="education_subscriptions")]
            ]),
        )
        await callback.answer()
        return

    await safe_edit_message(
        callback,
        "📅 *Select a plan:*",
        reply_markup=_subscriptions_keyboard(items, cat_code, buttons),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edu_sub:"))
async def edu_subscription_detail(callback: CallbackQuery, session: AsyncSession, state: FSMContext, mirror_bot_id: int, buttons):
    sub_id = int(callback.data.split(":", 1)[1])
    result = await session.execute(select(EducationSubscription).where(EducationSubscription.id == sub_id))
    sub = result.scalar_one_or_none()

    if not sub:
        await callback.answer("Subscription not found", show_alert=True)
        return

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    price = sub.price
    balance = user.balance if user else Decimal("0")

    desc = sub.description or ""
    text = (
        f"📅 *{sub.name}*\n\n"
        f"⏱ *Duration:* {sub.duration_days} days\n"
        f"💰 *Price:* ${price:.2f}\n"
        f"💳 *Your balance:* ${balance:.2f}\n"
        + (f"\n📝 {desc}\n" if desc else "") +
        f"\n⚠️ After payment, an order will be created and a worker will grant you access within "
        f"{ServiceETA.get_eta('lookup')}."
    )

    buy_btn_text = getattr(buttons, "EDU_BUY_SUBSCRIPTION", "✅ Buy Subscription")
    await safe_edit_message(
        callback,
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=buy_btn_text, callback_data=f"edu_sub_buy:{sub_id}")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="education_subscriptions")],
        ]),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edu_sub_buy:"))
async def edu_subscription_buy(callback: CallbackQuery, session: AsyncSession, state: FSMContext, mirror_bot_id: int, buttons):
    sub_id = int(callback.data.split(":", 1)[1])
    result = await session.execute(select(EducationSubscription).where(EducationSubscription.id == sub_id))
    sub = result.scalar_one_or_none()

    if not sub:
        await callback.answer("Subscription not found", show_alert=True)
        return

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    price = sub.price
    confirm_text = (
        f"⚠️ Confirm purchase?\n\n"
        f"📅 *Subscription:* {sub.name}\n"
        f"⏱ *Duration:* {sub.duration_days} days\n"
        f"💰 *Price:* ${price:.2f}\n"
        f"💳 *Your balance:* ${user.balance if user else Decimal('0'):.2f}\n"
    )
    await state.update_data(
        edu_subscription_id=sub_id,
        checkout_category="education_sub",
        checkout_service_name=sub.name,
        checkout_base_price=str(price),
        checkout_confirm_text=confirm_text,
        checkout_keyboard_type="custom",
        checkout_confirm_callback=f"edu_sub_confirm:{sub_id}",
        checkout_cancel_callback="education_subscriptions",
        checkout_parse_mode="Markdown",
        selected_coupon_code=None,
        selected_user_coupon_id=None,
    )
    await state.set_state(EducationStates.confirm_subscription)
    await safe_edit_message(
        callback,
        confirm_text,
        reply_markup=_education_confirm_keyboard(f"edu_sub_confirm:{sub_id}", "education_subscriptions", buttons),
        parse_mode="Markdown",
    )
    await callback.answer()


# ─── Manuals ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "education_manuals")
async def education_manuals_handler(callback: CallbackQuery, session: AsyncSession, buttons):
    categories = await _load_man_categories(session)
    counts = await MenuCountService.get_education_counts(session)
    if not categories:
        items = await _load_manuals(session)
        if not items:
            await safe_edit_message(
                callback,
                "📖 *Manuals*\n\nNo manuals available yet. Check back later!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=getattr(buttons, "EDU_BACK", "⬅️ Back"), callback_data="education_main")]
                ]),
                parse_mode="Markdown",
            )
            await callback.answer()
            return

        rows = []
        for item in items:
            rows.append([InlineKeyboardButton(
                text=f"📖 {item.name} — ${item.price}",
                callback_data=f"edu_man:{item.id}"
            )])
        rows.append([InlineKeyboardButton(text=getattr(buttons, "EDU_BACK", "⬅️ Back"), callback_data="education_main")])
        await safe_edit_message(
            callback,
            "📖 *Manuals*\n\nSelect a manual:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
            parse_mode="Markdown",
        )
        await callback.answer()
        return

    await safe_edit_message(
        callback,
        "📖 *Manuals*\n\nSelect a category:",
        reply_markup=_man_categories_keyboard(categories, buttons, counts["manuals_by_category"]),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edu_man_cat:"))
async def edu_manual_category_handler(callback: CallbackQuery, session: AsyncSession, buttons):
    cat_code = callback.data.split(":", 1)[1]
    items = await _load_manuals(session, cat_code)

    if not items:
        await safe_edit_message(
            callback,
            "📖 No manuals in this category yet.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Back", callback_data="education_manuals")]
            ]),
        )
        await callback.answer()
        return

    await safe_edit_message(
        callback,
        "📖 *Select a manual:*",
        reply_markup=_manuals_keyboard(items, cat_code, buttons),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edu_man:"))
async def edu_manual_detail(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int, buttons):
    man_id = int(callback.data.split(":", 1)[1])
    result = await session.execute(select(EducationManual).where(EducationManual.id == man_id))
    manual = result.scalar_one_or_none()

    if not manual:
        await callback.answer("Manual not found", show_alert=True)
        return

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    balance = user.balance if user else Decimal("0")
    desc = manual.description or ""

    text = (
        f"📖 *{manual.name}*\n\n"
        f"💰 *Price:* ${manual.price:.2f}\n"
        f"💳 *Your balance:* ${balance:.2f}\n"
        f"📄 *Format:* {manual.file_type.upper()}\n"
        + (f"\n📝 {desc}\n" if desc else "") +
        f"\n📥 File will be delivered automatically after payment."
    )

    buy_btn_text = getattr(buttons, "EDU_BUY_MANUAL", "📥 Buy Manual")
    await safe_edit_message(
        callback,
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=buy_btn_text, callback_data=f"edu_man_buy:{man_id}")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="education_manuals")],
        ]),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edu_man_buy:"))
async def edu_manual_buy(callback: CallbackQuery, session: AsyncSession, state: FSMContext, mirror_bot_id: int, buttons):
    man_id = int(callback.data.split(":", 1)[1])
    result = await session.execute(select(EducationManual).where(EducationManual.id == man_id))
    manual = result.scalar_one_or_none()

    if not manual or not manual.is_available:
        await callback.answer("Manual not available", show_alert=True)
        return

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    price = manual.price
    confirm_text = (
        f"⚠️ Confirm purchase?\n\n"
        f"📖 *Manual:* {manual.name}\n"
        f"📄 *Format:* {manual.file_type.upper()}\n"
        f"💰 *Price:* ${price:.2f}\n"
        f"💳 *Your balance:* ${user.balance if user else Decimal('0'):.2f}\n"
    )
    await state.update_data(
        edu_manual_id=man_id,
        checkout_category="education_manual",
        checkout_service_name=manual.name,
        checkout_base_price=str(price),
        checkout_confirm_text=confirm_text,
        checkout_keyboard_type="custom",
        checkout_confirm_callback=f"edu_man_confirm:{man_id}",
        checkout_cancel_callback="education_manuals",
        checkout_parse_mode="Markdown",
        selected_coupon_code=None,
        selected_user_coupon_id=None,
    )
    await state.set_state(EducationStates.confirm_manual)
    await safe_edit_message(
        callback,
        confirm_text,
        reply_markup=_education_confirm_keyboard(f"edu_man_confirm:{man_id}", "education_manuals", buttons),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edu_sub_confirm:"), EducationStates.confirm_subscription)
async def edu_subscription_confirm(callback: CallbackQuery, session: AsyncSession, state: FSMContext, mirror_bot_id: int):
    sub_id = int(callback.data.split(":", 1)[1])
    sub = await session.scalar(select(EducationSubscription).where(EducationSubscription.id == sub_id))
    if not sub:
        await callback.answer("Subscription not found", show_alert=True)
        return
    try:
        pricing = await CheckoutCouponService.get_checkout_pricing(
            session,
            telegram_user_id=callback.from_user.id,
            state_data=await state.get_data(),
        )
        success = await OrderService.deduct_balance(session, callback.from_user.id, pricing.final_amount)
        if not success:
            await callback.answer("Insufficient balance", show_alert=True)
            return
        order = await OrderService.create_order(
            session,
            user_id=callback.from_user.id,
            mirror_bot_id=mirror_bot_id,
            category="education_sub",
            service_name=sub.name,
            input_data={"subscription_id": sub_id, "subscription_code": sub.code, "duration_days": sub.duration_days},
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
            f"📅 *Subscription:* {sub.name}\n"
            f"⏱ *Duration:* {sub.duration_days} days\n"
            f"💰 *Paid:* ${pricing.final_amount:.2f}\n"
            f"💳 *Balance:* ${user.balance:.2f}\n\n"
            f"⏳ A worker will activate your subscription within {ServiceETA.get_eta('lookup')}.\n"
            f"📬 You'll receive confirmation here.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")]]),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Education subscription order failed: {e}")
        await callback.answer("Error creating order. Please try again.", show_alert=True)
    await callback.answer()


@router.callback_query(F.data.startswith("edu_man_confirm:"), EducationStates.confirm_manual)
async def edu_manual_confirm(callback: CallbackQuery, session: AsyncSession, state: FSMContext, mirror_bot_id: int):
    man_id = int(callback.data.split(":", 1)[1])
    manual = await session.scalar(select(EducationManual).where(EducationManual.id == man_id))
    if not manual or not manual.is_available:
        await callback.answer("Manual not available", show_alert=True)
        return
    try:
        pricing = await CheckoutCouponService.get_checkout_pricing(
            session,
            telegram_user_id=callback.from_user.id,
            state_data=await state.get_data(),
        )
        success = await OrderService.deduct_balance(session, callback.from_user.id, pricing.final_amount)
        if not success:
            await callback.answer("Insufficient balance", show_alert=True)
            return
        user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
        file_path = manual.file_path
        delivered = False
        if file_path and os.path.exists(file_path):
            try:
                from shared.services.pdf_watermark import generate_watermarked_pdf, render_pdf_pages_as_images
                pdf_bytes = generate_watermarked_pdf(file_path, user_id=callback.from_user.id, username=callback.from_user.username)
                page_images = render_pdf_pages_as_images(pdf_bytes)
                doc_file = BufferedInputFile(pdf_bytes, filename=manual.file_name)
                if page_images:
                    media_group = []
                    for idx, (image_name, image_bytes) in enumerate(page_images[:10]):
                        media_group.append(InputMediaPhoto(media=BufferedInputFile(image_bytes, filename=image_name), caption=f"📖 {manual.name}\nWatermarked preview pages" if idx == 0 else None))
                    await callback.bot.send_media_group(chat_id=callback.message.chat.id, media=media_group)
                await callback.message.answer_document(document=doc_file, caption=f"📖 *{manual.name}*\n\nThank you for your purchase! 🎉", parse_mode="Markdown")
                session.add(ManualDelivery(user_id=callback.from_user.id, username=callback.from_user.username, manual_id=man_id))
                await session.commit()
                delivered = True
            except Exception as e:
                logger.error(f"Failed to deliver watermarked manual {file_path}: {e}")
        if delivered:
            await state.clear()
            await safe_edit_message(
                callback,
                f"✅ *Purchase successful!*\n\n"
                f"📖 *Manual:* {manual.name}\n"
                f"💰 *Paid:* ${pricing.final_amount:.2f}\n"
                f"💳 *Balance:* ${user.balance:.2f}\n\n"
                f"📥 Your file has been sent above.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")]]),
                parse_mode="Markdown",
            )
        else:
            order = await OrderService.create_order(
                session,
                user_id=callback.from_user.id,
                mirror_bot_id=mirror_bot_id,
                category="education_manual",
                service_name=manual.name,
                input_data={"manual_id": man_id, "manual_code": manual.code},
                price=pricing.final_amount,
                original_price=pricing.original_amount,
                coupon_code=pricing.code,
                discount_amount=pricing.discount_amount,
                coupon_application=pricing,
            )
            await state.clear()
            await safe_edit_message(
                callback,
                f"✅ *Order #{order.id} created!*\n\n"
                f"📖 *Manual:* {manual.name}\n"
                f"💰 *Paid:* ${pricing.final_amount:.2f}\n"
                f"💳 *Balance:* ${user.balance:.2f}\n\n"
                f"⚠️ File delivery is in progress. You'll receive it shortly.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")]]),
                parse_mode="Markdown",
            )
    except Exception as e:
        logger.error(f"Manual purchase failed: {e}")
        await callback.answer("Error processing purchase. Please try again.", show_alert=True)
    await callback.answer()
