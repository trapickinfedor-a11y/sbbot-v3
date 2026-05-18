from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError
from decimal import Decimal

from mirror_bot.keyboards.inline import InlineKeyboardMarkup, InlineKeyboardButton, confirm_keyboard
from sqlalchemy import select as _sa_select
from mirror_bot.constants.states_data import STATES_PAGES, US_STATES
from mirror_bot.constants.prices import ServicePrices
from mirror_bot.constants.service_eta import ServiceETA
from mirror_bot.middlewares.language import LanguageHelper
from mirror_bot.utils.message_utils import safe_edit_message, safe_answer_callback
from mirror_bot.states.order import DocumentStates
from mirror_bot.services.validator import DocumentOrderData, parse_freeform_text
from mirror_bot.services.order_service import OrderService
from mirror_bot.services.checkout_coupon_service import CheckoutCouponService
from mirror_bot.services.user_service import UserService
from mirror_bot.utils.product_translations import ProductTranslations
from mirror_bot.services.product_service import ProductService
from mirror_bot.constants.buttons_en import ButtonTexts
from mirror_bot.services.menu_counts_service import MenuCountService
from shared.services.product_catalog_service import ProductCatalogManager
from mirror_bot.utils.media_library import resolve_bot_photo
import logging

logger = logging.getLogger(__name__)

router = Router()

DOCUMENT_SERVICE_FALLBACK_NAMES = {
    "dl_front_back": "DL (Front & Back)",
    "dl_selfie": "DL + Selfie",
    "dl_kyc": "DL + KYC video",
    "passport": "Passport",
    "business_docs": "Business Docs",
}

HARDCODED_DOC_SERVICES = ["dl_front_back", "dl_selfie", "dl_kyc", "passport", "business_docs"]

HARDCODED_BUTTON_MAP = {
    "dl_front_back": "DL_FRONT_BACK",
    "dl_selfie": "DL_SELFIE",
    "dl_kyc": "DL_KYC",
    "passport": "PASSPORT",
    "business_docs": "BUSINESS_DOCS",
}

STATES_PER_PAGE = 10

ALL_STATES_FLAT = []
for page in STATES_PAGES:
    ALL_STATES_FLAT.extend(page)


async def _get_document_services(session: AsyncSession, menu_group: str):
    await ProductCatalogManager.ensure_defaults(session)
    return await ProductCatalogManager.list_services(
        session,
        category_key="docs",
        menu_group=menu_group,
        active_only=True,
    )


async def _resolve_document_service_name(session: AsyncSession, service_code: str) -> str:
    catalog_service = await ProductCatalogManager.get_service(session, service_code)
    if catalog_service:
        return catalog_service.name
    return DOCUMENT_SERVICE_FALLBACK_NAMES.get(service_code, ProductCatalogManager.format_service_label(service_code))


def _format_count(count) -> str:
    if count is None or count == "?":
        return ""
    count = int(count)
    if count == 0:
        return ""
    return f" [{count}]"


def documents_main_keyboard(buttons, direct_services=None, counts=None):
    counts = counts or {}
    checks_text = getattr(buttons, "DOCS_CHECKS", "📄 Checks")
    rows = []

    if direct_services:
        for service in direct_services:
            cnt = counts.get(service.code, 0)
            rows.append([InlineKeyboardButton(
                text=f"🪪 {service.name}{_format_count(cnt)}",
                callback_data=f"doc_photo_{service.code}",
            )])
    else:
        for code in HARDCODED_DOC_SERVICES:
            btn_attr = HARDCODED_BUTTON_MAP[code]
            label = getattr(buttons, btn_attr, code)
            cnt = counts.get(code, 0)
            rows.append([InlineKeyboardButton(
                text=f"{label}{_format_count(cnt)}",
                callback_data=f"doc_photo_{code}",
            )])

    checks_cnt = counts.get("checks", 0)
    rows.append([InlineKeyboardButton(
        text=f"{checks_text}{_format_count(checks_cnt)}",
        callback_data="doc_checks",
    )])
    rows.append([InlineKeyboardButton(text=buttons.HIGH_QUALITY_DRAWING_COMING_SOON, callback_data="doc_drawing_high")])
    rows.append([InlineKeyboardButton(text=buttons.BACK, callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def doc_states_keyboard(doc_type: str, page: int, buttons, state_counts: dict | None = None):
    state_counts = state_counts or {}
    total_states = len(ALL_STATES_FLAT)
    total_pages = max(1, (total_states + STATES_PER_PAGE - 1) // STATES_PER_PAGE)
    page = max(0, min(page, total_pages - 1))

    start = page * STATES_PER_PAGE
    end = min(start + STATES_PER_PAGE, total_states)
    page_states = ALL_STATES_FLAT[start:end]

    keyboard_buttons = []
    for name, code in page_states:
        cnt = state_counts.get(code, 0)
        cnt_text = f" [{cnt}]" if cnt else ""
        keyboard_buttons.append([InlineKeyboardButton(
            text=f"{name}, {code}{cnt_text}",
            callback_data=f"doc_{doc_type}_state:{code}",
        )])

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text=buttons.PREV, callback_data=f"doc_{doc_type}_page:{page - 1}"))
    page_text = buttons.PAGE_INFO.format(page=page + 1, total_pages=total_pages)
    nav_row.append(InlineKeyboardButton(text=page_text, callback_data="doc_state_noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text=buttons.NEXT, callback_data=f"doc_{doc_type}_page:{page + 1}"))
    keyboard_buttons.append(nav_row)

    keyboard_buttons.append([InlineKeyboardButton(text=buttons.BACK, callback_data="doc_back_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


async def _build_counts_dict(session: AsyncSession) -> dict:
    documents_counts = await MenuCountService.get_documents_counts(session)
    return {
        "checks": documents_counts.get("checks", 0),
        **documents_counts.get("by_service", {}),
    }


@router.message(F.text.func(lambda value: ButtonTexts.matches("DOCUMENTS", value)))
async def documents_main_handler(message: Message, session: AsyncSession, texts, buttons):
    direct_services = await _get_document_services(session, "documents_direct")
    counts = await _build_counts_dict(session)
    docs_photo = resolve_bot_photo("documents", "docs", fallback_path="media/Docs.jpg")
    kb = documents_main_keyboard(buttons, direct_services, counts)
    try:
        if docs_photo:
            await message.answer_photo(
                photo=docs_photo,
                caption=f"{buttons.DOCUMENTS}\n\n{texts.DOCUMENTS_MAIN}",
                reply_markup=kb,
            )
        else:
            raise RuntimeError("no photo")
    except Exception:
        await message.answer(
            f"{buttons.DOCUMENTS}\n\n{texts.DOCUMENTS_MAIN}",
            reply_markup=kb,
        )


@router.callback_query(F.data == "doc_back_main")
async def doc_back_main_callback(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    direct_services = await _get_document_services(session, "documents_direct")
    counts = await _build_counts_dict(session)
    docs_photo = resolve_bot_photo("documents", "docs", fallback_path="media/Docs.jpg")
    kb = documents_main_keyboard(buttons, direct_services, counts)
    try:
        await callback.message.delete()
        if docs_photo:
            await callback.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=docs_photo,
                caption=f"{buttons.DOCUMENTS}\n\n{texts.DOCUMENTS_MAIN}",
                reply_markup=kb,
            )
        else:
            raise RuntimeError("no photo")
    except Exception:
        await safe_edit_message(
            callback,
            f"{buttons.DOCUMENTS}\n\n{texts.DOCUMENTS_MAIN}",
            reply_markup=kb,
        )
    await callback.answer()


@router.callback_query(F.data == "doc_checks")
async def doc_checks_handler(callback: CallbackQuery, session: AsyncSession, buttons):
    from shared.database.models import Seller, SellerCheckItem
    items = list((await session.execute(
        _sa_select(SellerCheckItem)
        .join(Seller)
        .where(
            SellerCheckItem.is_active == True,
            SellerCheckItem.is_in_stock == True,
            SellerCheckItem.moderation_status == "approved",
            Seller.is_approved == True,
            Seller.is_active == True,
        )
        .limit(20)
    )).scalars().all())
    rows = [
        [InlineKeyboardButton(
            text=f"📄 {getattr(item, 'check_type', getattr(item, 'bank_name', ''))} | ${float(item.price):.2f}",
            callback_data=f"seller_specials_detail:checks:{item.id}",
        )]
        for item in items
    ]
    if not rows:
        rows.append([InlineKeyboardButton(text="No items available", callback_data="doc_back_main")])
    rows.append([InlineKeyboardButton(text="⬅️ Back to Documents", callback_data="doc_back_main")])
    await safe_edit_message(
        callback,
        "*📄 Checks*\n\nSelect item:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "doc_drawing_high")
async def doc_drawing_high_handler(callback: CallbackQuery, texts, buttons):
    await safe_edit_message(
        callback,
        texts.HIGH_QUALITY_DRAWING_COMING_SOON,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=buttons.BACK, callback_data="doc_back_main")]
        ]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("doc_photo_"))
async def doc_photo_item_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession, texts, buttons):
    item_type = callback.data.replace("doc_photo_", "")

    service_aliases = {
        "dl": "dl_front_back",
        "biz": "business_docs",
    }
    service_code = service_aliases.get(item_type, item_type)
    name = await _resolve_document_service_name(session, service_code)

    await state.update_data(doc_type=service_code)

    state_counts = await MenuCountService.build_documents_state_counts(session, service_code)

    await safe_edit_message(
        callback,
        f"{name}\n\n{texts.SELECT_STATE}",
        reply_markup=doc_states_keyboard(service_code, page=0, buttons=buttons, state_counts=state_counts),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("doc_") & F.data.contains("_page:"))
async def doc_state_page_handler(callback: CallbackQuery, session: AsyncSession, texts, buttons):
    parts = callback.data.split("_page:")
    doc_type = parts[0].replace("doc_", "")
    page = int(parts[1])

    service_aliases = {"dl": "dl_front_back", "biz": "business_docs"}
    service_code = service_aliases.get(doc_type, doc_type)

    name = await _resolve_document_service_name(session, service_code)
    state_counts = await MenuCountService.build_documents_state_counts(session, service_code)

    await safe_edit_message(
        callback,
        f"{name}\n\n{texts.SELECT_STATE}",
        reply_markup=doc_states_keyboard(doc_type, page=page, buttons=buttons, state_counts=state_counts),
    )
    await callback.answer()


@router.callback_query(F.data == "doc_state_noop")
async def doc_state_noop_handler(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("doc_") & F.data.contains("_state:"))
async def doc_state_selected_handler(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    parts = callback.data.split("_state:")
    doc_type = parts[0].replace("doc_", "")
    selected_state = parts[1]

    service_aliases = {
        "dl": "dl_front_back",
        "biz": "business_docs",
    }
    service = service_aliases.get(doc_type, doc_type)
    if not service:
        from mirror_bot.constants.language_loader import get_texts
        texts = get_texts('en')
        await safe_answer_callback(callback, texts.DOCUMENT_UNKNOWN_TYPE, show_alert=True)
        return

    from mirror_bot.handlers.products import show_products_for_state

    class TempCallback:
        def __init__(self, original_callback, new_data):
            self.data = new_data
            self.message = original_callback.message
            self.from_user = original_callback.from_user
            self.bot = original_callback.bot

        async def answer(self, *args, **kwargs):
            return await callback.answer(*args, **kwargs)

    temp_callback = TempCallback(callback, f"show_products:docs:{service}:{selected_state}")
    await show_products_for_state(temp_callback, state, session)


@router.message(DocumentStates.waiting_data, F.text)
async def document_data_handler(message: Message, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    data = await state.get_data()
    doc_type = data.get("doc_type")
    selected_state = data.get("selected_state")
    service_name = data.get("service_name")
    price = data.get("price")

    text = message.text.strip()

    parsed_data = parse_freeform_text(text, required_fields=["first_name", "last_name", "address", "city", "zip"])

    if parsed_data.get("errors"):
        issues_text = "\n".join([f"• {issue}" for issue in parsed_data["errors"]])
        example = texts.DOCUMENT_EXAMPLE_FORMAT.format(state=selected_state)
        await message.answer(
            texts.DOCUMENT_INVALID_DATA.format(issues_text=issues_text, example=example)
        )
        return

    try:
        parsed_data["state"] = selected_state

        validated_data = DocumentOrderData(
            first_name=parsed_data["first_name"],
            last_name=parsed_data["last_name"],
            address=parsed_data["address"],
            city=parsed_data["city"],
            state=selected_state,
            zip_code=parsed_data["zip"],
            dob=parsed_data.get("dob")
        )

        info_lines = [
            f"👤 `{validated_data.first_name} {validated_data.last_name}`",
            f"📍 `{validated_data.address}`",
            f"🏙️ `{validated_data.city}, {validated_data.state} {validated_data.zip_code}`",
        ]

        if hasattr(validated_data, 'ssn') and validated_data.ssn:
            info_lines.append(f"🆔 SSN: `{validated_data.ssn}`")

        if validated_data.dob:
            info_lines.append(f"🎂 DOB: `{validated_data.dob}`")

        if hasattr(validated_data, 'phone') and validated_data.phone:
            info_lines.append(f"📞 Phone: `{validated_data.phone}`")

        if hasattr(validated_data, 'email') and validated_data.email:
            info_lines.append(f"📧 Email: {validated_data.email}")

        confirmation_text = texts.ORDER_CONFIRMATION.format(
            service_name=service_name,
            price=price
        ) + "\n\n" + "\n".join(info_lines)

        await state.update_data(
            validated_data=validated_data.dict(),
            checkout_category="documents",
            checkout_service_name=f"doc_{doc_type}",
            checkout_base_price=str(price),
            checkout_confirm_text=confirmation_text,
            checkout_keyboard_type="confirm",
            checkout_keyboard_suffix="_doc",
            checkout_parse_mode="Markdown",
            selected_coupon_code=None,
            selected_user_coupon_id=None,
        )
        await state.set_state(DocumentStates.confirmation)

        await message.answer(confirmation_text, reply_markup=confirm_keyboard(buttons, suffix="_doc"), parse_mode="Markdown")

    except ValidationError as e:
        errors = "\n".join([f"• {err['msg']}" for err in e.errors()])
        example = texts.DOCUMENT_EXAMPLE_FORMAT.format(state=selected_state)
        await message.answer(
            texts.DOCUMENT_VALIDATION_ERROR.format(errors=errors, example=example)
        )


@router.callback_query(F.data == "confirm_yes_doc", DocumentStates.confirmation)
async def confirm_document_order(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int, texts, buttons):
    data = await state.get_data()
    doc_type = data.get("doc_type")
    validated_data = data.get("validated_data")
    price = data.get("price")
    service_name = data.get("service_name")

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    pricing = await CheckoutCouponService.get_checkout_pricing(
        session,
        telegram_user_id=callback.from_user.id,
        state_data=data,
    )

    if user.balance < pricing.final_amount:
        await safe_edit_message(callback,
            texts.INSUFFICIENT_BALANCE.format(
                balance=user.balance,
                price=pricing.final_amount
            )
        )
        await state.clear()
        await callback.answer()
        return

    success = await OrderService.deduct_balance(session, callback.from_user.id, pricing.final_amount)

    if not success:
        await callback.answer(texts.INSUFFICIENT_BALANCE_ALERT, show_alert=True)
        return

    order = await OrderService.create_order(
        session,
        user_id=callback.from_user.id,
        mirror_bot_id=mirror_bot_id,
        category="documents",
        service_name=f"doc_{doc_type}",
        input_data=validated_data,
        price=pricing.final_amount,
        original_price=pricing.original_amount,
        coupon_code=pricing.code,
        discount_amount=pricing.discount_amount,
        coupon_application=pricing,
    )

    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)

    user_language = user.language if user and hasattr(user, 'language') else 'en'
    category_name = ProductTranslations.get_category_name("documents", user_language)
    service_id = f"{doc_type}_doc"
    service_name = ProductTranslations.get_service_name(service_id, user_language)

    product_name = service_name
    if data.get('state'):
        product_name += f" - {data.get('state')}"

    eta = ServiceETA.get_eta(service_id)

    await safe_edit_message(
        callback,
        texts.ORDER_CREATED.format(
            product=product_name,
            price=pricing.final_amount,
            balance=user.balance,
            eta=eta
        ),
        parse_mode="Markdown"
    )
    await state.clear()
    await callback.answer(texts.ORDER_CREATED_SUCCESS)


@router.callback_query(F.data == "confirm_no_doc", DocumentStates.confirmation)
async def cancel_document_order(callback: CallbackQuery, state: FSMContext, texts, buttons):
    await safe_edit_message(callback, texts.ORDER_CANCELLED)
    await state.clear()
    await callback.answer()
