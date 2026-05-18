from __future__ import annotations

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal, InvalidOperation

from seller_bot.keyboards.inline import (
    seller_bank_list, seller_bank_detail, category_keyboard,
    confirm_delete_keyboard, seller_main_menu,
    add_mode_keyboard, bank_type_keyboard, support_mode_keyboard,
    bank_product_type_keyboard, bank_product_subtype_keyboard,
    bank_number_access_keyboard, bank_number_change_keyboard, bank_auto_unpublish_keyboard
)
from seller_bot.services.stock_service import StockService
from shared.services.seller_upload_batch_service import SellerUploadBatchService
from shared.services.seller_deposit_service import SellerDepositService
from shared.utils.seller_product_meta import bank_item_badge, bank_type_label, bank_subtype_label
from shared.services.seller_upload_pipeline_service import SellerUploadPipelineService
from shared.services.nocodb_service import NocoDBService

logger = logging.getLogger(__name__)
router = Router(name="seller_stock")


class AddBankStates(StatesGroup):
    waiting_product_type = State()
    waiting_product_subtype = State()
    waiting_category = State()
    waiting_add_mode = State()  # existing vs new vs request
    waiting_bank_type = State()  # for existing: pick from catalog
    waiting_name = State()  # for new: custom name
    waiting_request_bank_name = State()  # for request: bank name
    waiting_request_state = State()  # for request: state
    waiting_request_zip = State()  # for request: zip
    waiting_request_has_docs = State()  # for request: has docs
    waiting_request_doc_type = State()  # for request: doc type
    waiting_request_description = State()  # for request: description
    waiting_price = State()
    waiting_description = State()
    waiting_instruction = State()
    waiting_extra_text = State()
    waiting_extra_bool = State()
    waiting_support_mode = State()
    waiting_number_access = State()
    waiting_rental_days = State()
    waiting_number_change_allowed = State()
    waiting_auto_unpublish = State()
    waiting_listing_duration_days = State()
    waiting_stock_count = State()
    confirmation = State()


class EditPriceStates(StatesGroup):
    waiting_new_price = State()


class EditQtyStates(StatesGroup):
    waiting_new_qty = State()


def _bank_submit_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Submit", callback_data="seller_bank_submit_confirm")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")],
    ])


def _bank_bool_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yes", callback_data="seller_bank_extra_bool:yes"),
            InlineKeyboardButton(text="❌ No", callback_data="seller_bank_extra_bool:no"),
        ],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")],
    ])


def _bank_extra_specs(product_type: str, product_subtype: str) -> list[dict]:
    if product_type == "enrol":
        return [
            {"name": "portal", "kind": "text", "prompt": "🔐 Enter portal (example: FDECS, DIGITALCARDSERVICE, MYCARDINFO, CARDNAV):"},
            {"name": "card_type", "kind": "text", "prompt": "💳 Enter card type (Visa / MC / Amex / Discover):"},
            {"name": "state", "kind": "text", "prompt": "🗺 Enter state:"},
            {"name": "zip", "kind": "text", "prompt": "📮 Enter ZIP:"},
            {"name": "has_ssn", "kind": "bool", "prompt": "SSN included?"},
            {"name": "has_dob", "kind": "bool", "prompt": "DOB included?"},
            {"name": "has_name", "kind": "bool", "prompt": "Name included?"},
            {"name": "has_address", "kind": "bool", "prompt": "Address included?"},
            {"name": "has_email", "kind": "bool", "prompt": "Email included?"},
            {"name": "has_security_qa", "kind": "bool", "prompt": "Security Q/A included?"},
            {"name": "has_docs", "kind": "bool", "prompt": "Docs included?"},
            {"name": "doc_type", "kind": "text", "prompt": "📄 Enter doc type (Driver License / Passport / SSN Card) or - to skip:", "skip_if": lambda data: not data.get("has_docs")},
            {"name": "phone_area_code", "kind": "text", "prompt": "📱 Enter phone area code (or - to skip):"},
        ]
    if product_subtype == "selfreg":
        return [
            {"name": "state", "kind": "text", "prompt": "🗺 Enter state:"},
            {"name": "zip", "kind": "text", "prompt": "📮 Enter ZIP:"},
            {"name": "has_ssn", "kind": "bool", "prompt": "SSN included?"},
            {"name": "has_docs", "kind": "bool", "prompt": "Docs included?"},
            {"name": "doc_type", "kind": "text", "prompt": "📄 Enter doc type (Driver License / Passport / SSN Card) or - to skip:", "skip_if": lambda data: not data.get("has_docs")},
        ]
    if product_subtype == "log":
        return [
            {"name": "details_text", "kind": "text", "prompt": "📋 Send structured log text with accounts and flags.\n\nExample lines:\nChecking: $4064.18\nSavings: $20708.56\nCC avb: $17159.00 [BT ✅] [CVV ✅]\nZelle enroll\nSafepass +🔓", "multiline": True},
        ]
    return []


async def _advance_bank_extra_flow(message_target, state: FSMContext):
    data = await state.get_data()
    specs = _bank_extra_specs(data.get("product_type", "bank"), data.get("product_subtype", "log"))
    index = int(data.get("extra_step_index", 0) or 0)
    while index < len(specs):
        spec = specs[index]
        if spec.get("skip_if") and spec["skip_if"](data):
            index += 1
            await state.update_data(extra_step_index=index)
            continue
        await state.update_data(extra_step_index=index, extra_current_field=spec["name"])
        if spec["kind"] == "bool":
            await state.set_state(AddBankStates.waiting_extra_bool)
            await message_target.answer(spec["prompt"], reply_markup=_bank_bool_keyboard())
        else:
            await state.set_state(AddBankStates.waiting_extra_text)
            await message_target.answer(spec["prompt"])
        return

    await state.set_state(AddBankStates.waiting_support_mode)
    await message_target.answer(
        "💬 Select support mode for this material:\n\n"
        "If chat is enabled, buyer will be able to write to you.\n"
        "If disabled, buyer will only get a guarantee flow without seller chat.",
        reply_markup=support_mode_keyboard(),
    )


@router.callback_query(F.data == "seller_my_banks")
async def my_banks_handler(callback: CallbackQuery, session: AsyncSession, seller, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    if not seller or not seller_actor or not seller_actor.can_upload():
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    
    banks = await StockService.get_seller_banks(session, seller.id)
    
    if not banks:
        await callback.message.edit_text(
            "🏦 <b>My Banks</b>\n\n"
            "You don't have any banks yet.\n"
            "Press <b>Add Bank</b> to create your first position.",
            reply_markup=seller_bank_list([])
        )
    else:
        in_stock = sum(1 for b in banks if b.is_in_stock)
        total_qty = sum(max(0, int(getattr(b, "stock_count", 0) or 0)) for b in banks)
        await callback.message.edit_text(
            f"🏦 <b>My Banks</b> ({len(banks)} total)\n\n"
            f"✅ In stock: {in_stock}\n"
            f"❌ Out of stock: {len(banks) - in_stock}\n"
            f"📦 Total quantity: {total_qty}\n\n"
            f"Tap a bank to manage it:",
            reply_markup=seller_bank_list(banks)
        )
    await callback.answer()


@router.callback_query(F.data == "seller_add_bank")
async def add_bank_start(callback: CallbackQuery, state: FSMContext, seller, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    if not seller or not seller_actor or not seller_actor.can_upload():
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    if not SellerDepositService.has_upload_access(seller, "bank"):
        await callback.answer(
            "❌ Bank package deposit is required before you can upload Bank or Enrol items.",
            show_alert=True
        )
        return
    
    await state.set_state(AddBankStates.waiting_product_type)
    await callback.message.edit_text(
        "➕ <b>Add New Item</b>\n\n"
        "Select material type:",
        reply_markup=bank_product_type_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_product_type:"), AddBankStates.waiting_product_type)
async def add_bank_product_type(callback: CallbackQuery, state: FSMContext, **kwargs):
    product_type = callback.data.split(":")[1]
    await state.update_data(product_type=product_type)
    await state.set_state(AddBankStates.waiting_product_subtype)
    await callback.message.edit_text(
        f"🧩 Type: <b>{bank_type_label(product_type)}</b>\n\n"
        "Select subtype:",
        reply_markup=bank_product_subtype_keyboard(product_type)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_product_subtype:"), AddBankStates.waiting_product_subtype)
async def add_bank_product_subtype(callback: CallbackQuery, state: FSMContext, **kwargs):
    product_subtype = callback.data.split(":")[1]
    data = await state.get_data()
    product_type = data.get("product_type", "bank")

    if product_subtype == "brute":
        await state.clear()
        await callback.message.edit_text(
            "🔓 <b>Brute Bank</b>\n\n"
            "Brute uses the dedicated flow because it requires credentials, range and account type.\n\n"
            "Open <b>Brute Bank</b> from the seller menu to continue.",
            reply_markup=seller_main_menu()
        )
        await callback.answer("Brute uses a separate flow", show_alert=True)
        return

    await state.update_data(product_subtype=product_subtype)
    await state.set_state(AddBankStates.waiting_category)
    await callback.message.edit_text(
        f"🧩 Type: <b>{bank_type_label(product_type)}</b>\n"
        f"🏷 Subtype: <b>{bank_subtype_label(product_subtype)}</b>\n\n"
        "Select category:",
        reply_markup=category_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_cat:"), AddBankStates.waiting_category)
async def add_bank_category(callback: CallbackQuery, state: FSMContext, **kwargs):
    category = callback.data.split(":")[1]
    await state.update_data(category=category)
    await state.set_state(AddBankStates.waiting_add_mode)
    
    cat_names = {"vcc": "VCC", "personal": "Personal Bank", "business": "Business Bank", "crypto": "Crypto", "merchant": "Merchant"}
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"🧩 Product: <b>{bank_item_badge(data.get('product_type', 'bank'), data.get('product_subtype', 'log'))}</b>\n"
        f"📝 Category: <b>{cat_names.get(category, category)}</b>\n\n"
        f"Choose how to add:\n"
        f"• <b>Add to existing type</b> — select from catalog (Chime, Chase, etc.)\n"
        f"• <b>Request new bank</b> — submit for admin approval (with details)\n"
        f"• <b>Create new type</b> — enter your own bank name (direct)",
        reply_markup=add_mode_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_add_mode:"), AddBankStates.waiting_add_mode)
async def add_bank_mode(callback: CallbackQuery, state: FSMContext, session: AsyncSession, **kwargs):
    mode = callback.data.split(":")[1]
    data = await state.get_data()
    category = data["category"]
    
    if mode == "existing":
        from shared.catalog import get_bank_types_for_category
        bank_types = await get_bank_types_for_category(session, category)
        if not bank_types:
            await callback.answer("No bank types in this category. Use Create new type.", show_alert=True)
            return
        
        await state.set_state(AddBankStates.waiting_bank_type)
        await callback.message.edit_text(
            f"📋 Select the <b>bank type</b> from catalog:",
            reply_markup=bank_type_keyboard(bank_types, category)
        )
    elif mode == "request":
        # Request new bank type for moderation
        await state.set_state(AddBankStates.waiting_request_bank_name)
        cat_names = {"vcc": "VCC", "personal": "Personal Bank", "business": "Business Bank", "crypto": "Crypto", "merchant": "Merchant"}
        await callback.message.edit_text(
            f"📝 <b>Request New Bank Type</b>\n\n"
            f"Category: <b>{cat_names.get(category, category)}</b>\n\n"
            f"Enter the <b>bank name</b> you want to add:\n"
            f"Example: <i>Chase Personal, Chime VCC, Coinbase</i>\n\n"
            f"⚠️ This will be reviewed by admin within 1-6 hours.\n"
            f"You cannot upload to this bank until it is approved."
        )
    else:
        # Create new type (direct, no moderation)
        await state.set_state(AddBankStates.waiting_name)
        cat_names = {"vcc": "VCC", "personal": "Personal Bank", "business": "Business Bank", "crypto": "Crypto", "merchant": "Merchant"}
        await callback.message.edit_text(
            f"📝 Category: <b>{cat_names.get(category, category)}</b>\n\n"
            f"Enter the <b>bank name</b> (new type):\n"
            f"Example: <i>Chase Personal, Chime VCC, Coinbase</i>"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_bank_type:"), AddBankStates.waiting_bank_type)
async def add_bank_type_selected(callback: CallbackQuery, state: FSMContext, session: AsyncSession, **kwargs):
    parts = callback.data.split(":")
    category = parts[1]
    bank_code = parts[2]
    
    from shared.catalog import get_bank_name_by_id
    bank_name = await get_bank_name_by_id(session, bank_code) or bank_code
    
    await state.update_data(bank_code=bank_code, bank_name=bank_name)
    await state.set_state(AddBankStates.waiting_price)
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"🏦 Bank: <b>{bank_name}</b>\n"
        f"🧩 Product: <b>{bank_item_badge(data.get('product_type', 'bank'), data.get('product_subtype', 'log'))}</b>\n\n"
        f"Enter your <b>price in USD</b>:\n"
        f"Example: <i>50</i> or <i>120.50</i>\n\n"
        f"This is your base price. Final buyer price is assigned during moderation."
    )
    await callback.answer()


@router.message(AddBankStates.waiting_name, F.text)
async def add_bank_name(message: Message, state: FSMContext, **kwargs):
    bank_name = message.text.strip()
    if len(bank_name) < 2 or len(bank_name) > 100:
        await message.answer("❌ Bank name must be 2-100 characters. Try again:")
        return
    
    await state.update_data(bank_name=bank_name)
    await state.set_state(AddBankStates.waiting_price)
    data = await state.get_data()
    
    await message.answer(
        f"🏦 Bank: <b>{bank_name}</b>\n"
        f"🧩 Product: <b>{bank_item_badge(data.get('product_type', 'bank'), data.get('product_subtype', 'log'))}</b>\n\n"
        f"Now enter your <b>price in USD</b>:\n"
        f"Example: <i>50</i> or <i>120.50</i>\n\n"
        f"This is your base price. Final buyer price is assigned during moderation."
    )


# ─── Request new bank flow ────────────────────────────────────────────────────

@router.message(AddBankStates.waiting_request_bank_name, F.text)
async def add_bank_request_name(message: Message, state: FSMContext, **kwargs):
    bank_name = message.text.strip()
    if len(bank_name) < 2:
        await message.answer("❌ Bank name too short. Try again:")
        return
    
    await state.update_data(request_bank_name=bank_name)
    await state.set_state(AddBankStates.waiting_request_state)
    await message.answer(
        "🗺 Enter the <b>state</b> (2-letter code, e.g. CA, NY):\n\n"
        "This helps admin categorize the bank.\n"
        "Send <b>-</b> if not applicable."
    )


@router.message(AddBankStates.waiting_request_state, F.text)
async def add_bank_request_state(message: Message, state: FSMContext, **kwargs):
    state_text = message.text.strip()
    state_value = None if state_text == "-" else state_text.upper()[:2]
    
    await state.update_data(request_state=state_value)
    await state.set_state(AddBankStates.waiting_request_zip)
    await message.answer(
        "📮 Enter the <b>ZIP code</b>:\n\n"
        "Send <b>-</b> if not applicable."
    )


@router.message(AddBankStates.waiting_request_zip, F.text)
async def add_bank_request_zip(message: Message, state: FSMContext, **kwargs):
    zip_text = message.text.strip()
    zip_value = None if zip_text == "-" else zip_text
    
    await state.update_data(request_zip=zip_value)
    await state.set_state(AddBankStates.waiting_request_has_docs)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yes", callback_data="seller_bank_request_docs:yes"),
            InlineKeyboardButton(text="❌ No", callback_data="seller_bank_request_docs:no"),
        ],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")],
    ])
    
    await message.answer(
        "📄 Are <b>documents</b> included with this bank type?\n\n"
        "(Driver License, Passport, SSN Card, etc.)",
        reply_markup=kb
    )


@router.callback_query(F.data.startswith("seller_bank_request_docs:"), AddBankStates.waiting_request_has_docs)
async def add_bank_request_has_docs(callback: CallbackQuery, state: FSMContext, **kwargs):
    has_docs = callback.data.split(":")[1] == "yes"
    await state.update_data(request_has_docs=has_docs)
    
    if has_docs:
        await state.set_state(AddBankStates.waiting_request_doc_type)
        await callback.message.edit_text(
            "📄 Enter the <b>document type</b>:\n\n"
            "Examples:\n"
            "• Driver License\n"
            "• Passport\n"
            "• SSN Card\n"
            "• ID Card\n\n"
            "Send <b>-</b> to skip."
        )
    else:
        await state.update_data(request_doc_type=None)
        await state.set_state(AddBankStates.waiting_request_description)
        await callback.message.edit_text(
            "📝 Enter a <b>description</b> for this bank type:\n\n"
            "⚠️ <b>This description will be shown to buyers.</b>\n\n"
            "Include important details like:\n"
            "• What's included\n"
            "• Special features\n"
            "• Usage notes\n\n"
            "Send <b>-</b> to skip."
        )
    
    await callback.answer()


@router.message(AddBankStates.waiting_request_doc_type, F.text)
async def add_bank_request_doc_type(message: Message, state: FSMContext, **kwargs):
    doc_type = message.text.strip()
    doc_value = None if doc_type == "-" else doc_type
    
    await state.update_data(request_doc_type=doc_value)
    await state.set_state(AddBankStates.waiting_request_description)
    await message.answer(
        "📝 Enter a <b>description</b> for this bank type:\n\n"
        "⚠️ <b>This description will be shown to buyers.</b>\n\n"
        "Include important details like:\n"
        "• What's included\n"
        "• Special features\n"
        "• Usage notes\n\n"
        "Send <b>-</b> to skip."
    )


@router.message(AddBankStates.waiting_request_description, F.text)
async def add_bank_request_description(message: Message, state: FSMContext, session: AsyncSession, seller, **kwargs):
    description = message.text.strip()
    desc_value = None if description == "-" else description
    
    data = await state.get_data()
    
    # Save the request to database
    from shared.database.models import BankTypeRequest
    
    request = BankTypeRequest(
        seller_id=seller.id,
        requested_name=data["request_bank_name"],
        state=data.get("request_state"),
        zip=data.get("request_zip"),
        has_docs=bool(data.get("request_has_docs")),
        doc_type=data.get("request_doc_type"),
        description=desc_value,
        product_type=data.get("product_type", "bank"),
        product_subtype=data.get("product_subtype", "log"),
        category=data.get("category"),
        status="pending",
    )
    
    session.add(request)
    await session.commit()
    await session.refresh(request)
    
    await state.clear()
    
    await message.answer(
        "✅ <b>Bank type request submitted!</b>\n\n"
        f"🏦 Bank: <b>{data['request_bank_name']}</b>\n"
        f"🗺 State: <b>{data.get('request_state') or 'N/A'}</b>\n"
        f"📮 ZIP: <b>{data.get('request_zip') or 'N/A'}</b>\n"
        f"📄 Docs: <b>{'Yes' if data.get('request_has_docs') else 'No'}</b>\n"
        f"📝 Description: <b>{desc_value or 'N/A'}</b>\n\n"
        f"📋 Request ID: #{request.id}\n\n"
        f"⏳ Our team will review your request within 1-6 hours.\n"
        f"You will be notified when the bank type is approved.\n"
        f"You cannot upload to this bank until it is created."
    )


# ─── Continue with existing flow ──────────────────────────────────────────────


@router.message(AddBankStates.waiting_price, F.text)
async def add_bank_price(message: Message, state: FSMContext, **kwargs):
    try:
        price = Decimal(message.text.strip().replace("$", "").replace(",", "."))
        if price <= 0 or price > 50000:
            await message.answer("❌ Price must be between $0.01 and $50,000. Try again:")
            return
    except (InvalidOperation, ValueError):
        await message.answer("❌ Invalid price format. Enter a number like <i>50</i> or <i>120.50</i>:")
        return
    
    await state.update_data(seller_price=float(price))
    await state.set_state(AddBankStates.waiting_description)
    
    await message.answer(
        f"💰 Your price: <b>${price:.2f}</b>\n"
        f"📊 Final buyer price will be set by moderation.\n\n"
        f"Enter a short <b>description</b> (optional).\n"
        f"Send <b>-</b> to skip."
    )


@router.message(AddBankStates.waiting_description, F.text)
async def add_bank_description(message: Message, state: FSMContext, session: AsyncSession, seller, **kwargs):
    description = None if message.text.strip() == "-" else message.text.strip()
    
    await state.update_data(description=description)
    await state.set_state(AddBankStates.waiting_instruction)
    await message.answer(
        "📘 Enter a short <b>instruction</b> for this material (optional).\n\n"
        "Use it for delivery notes, ZIP/fullz details or usage hints.\n"
        "Send <b>-</b> to skip."
    )


@router.message(AddBankStates.waiting_instruction, F.text)
async def add_bank_instruction(message: Message, state: FSMContext, **kwargs):
    instruction = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(instruction=instruction)
    await state.update_data(extra_step_index=0)
    await _advance_bank_extra_flow(message, state)


@router.message(AddBankStates.waiting_extra_text, F.text)
async def add_bank_extra_text(message: Message, state: FSMContext, **kwargs):
    data = await state.get_data()
    field_name = data.get("extra_current_field")
    value = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(**{field_name: value, "extra_step_index": int(data.get("extra_step_index", 0) or 0) + 1})
    await _advance_bank_extra_flow(message, state)


@router.callback_query(F.data.startswith("seller_bank_extra_bool:"), AddBankStates.waiting_extra_bool)
async def add_bank_extra_bool(callback: CallbackQuery, state: FSMContext, **kwargs):
    data = await state.get_data()
    field_name = data.get("extra_current_field")
    value = callback.data.split(":")[1] == "yes"
    await state.update_data(**{field_name: value, "extra_step_index": int(data.get("extra_step_index", 0) or 0) + 1})
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await _advance_bank_extra_flow(callback.message, state)


@router.callback_query(F.data.startswith("seller_support_mode:"), AddBankStates.waiting_support_mode)
async def add_bank_support_mode(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, **kwargs):
    mode = callback.data.split(":")[1]
    has_chat = mode == "chat"
    await state.update_data(has_chat=has_chat)
    await callback.message.edit_text(
        "📱 Does this bank include number/phone access?",
        reply_markup=bank_number_access_keyboard(),
    )
    await state.set_state(AddBankStates.waiting_number_access)
    await callback.answer()


@router.callback_query(F.data.startswith("seller_bank_number_access:"), AddBankStates.waiting_number_access)
async def add_bank_number_access(callback: CallbackQuery, state: FSMContext, **kwargs):
    value = callback.data.split(":")[1] == "yes"
    await state.update_data(number_access_available=value)
    if value:
        await state.set_state(AddBankStates.waiting_rental_days)
        await callback.message.edit_text(
            "📆 Enter rental duration in days for number access:\n\nExample: <b>3</b> or <b>7</b>",
            parse_mode="HTML",
        )
    else:
        await state.set_state(AddBankStates.waiting_number_change_allowed)
        await callback.message.edit_text(
            "🔁 If number access is not included, can buyer request number change?",
            reply_markup=bank_number_change_keyboard(),
        )
    await callback.answer()


@router.message(AddBankStates.waiting_rental_days, F.text)
async def add_bank_rental_days(message: Message, state: FSMContext, **kwargs):
    try:
        rental_days = int(message.text.strip())
        if rental_days <= 0 or rental_days > 365:
            raise ValueError
    except ValueError:
        await message.answer("❌ Rental days must be a number from 1 to 365.")
        return
    await state.update_data(rental_days=rental_days, adaptive_report_enabled=True, number_change_allowed=False)
    await state.set_state(AddBankStates.waiting_auto_unpublish)
    await message.answer(
        "⏳ Do you want this item to auto-unpublish after a chosen number of days?",
        reply_markup=bank_auto_unpublish_keyboard(),
    )


@router.callback_query(F.data.startswith("seller_bank_number_change:"), AddBankStates.waiting_number_change_allowed)
async def add_bank_number_change_allowed(callback: CallbackQuery, state: FSMContext, **kwargs):
    value = callback.data.split(":")[1] == "yes"
    await state.update_data(number_change_allowed=value, rental_days=None, adaptive_report_enabled=False)
    await state.set_state(AddBankStates.waiting_auto_unpublish)
    await callback.message.edit_text(
        "⏳ Do you want this item to auto-unpublish after a chosen number of days?",
        reply_markup=bank_auto_unpublish_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_bank_auto_unpublish:"), AddBankStates.waiting_auto_unpublish)
async def add_bank_auto_unpublish(callback: CallbackQuery, state: FSMContext, **kwargs):
    enabled = callback.data.split(":")[1] == "yes"
    await state.update_data(auto_unpublish_enabled=enabled)
    if enabled:
        await state.set_state(AddBankStates.waiting_listing_duration_days)
        await callback.message.edit_text(
            "📅 Enter how many days this item should stay active before auto-unpublish:",
        )
    else:
        await state.update_data(listing_duration_days=None)
        await state.set_state(AddBankStates.waiting_stock_count)
        await callback.message.edit_text(
            "📦 Enter stock quantity for this bank:\n\n"
            "Send a positive number. If you send 0, the bank will be saved as out of stock.",
        )
    await callback.answer()


@router.message(AddBankStates.waiting_listing_duration_days, F.text)
async def add_bank_listing_duration_days(message: Message, state: FSMContext, **kwargs):
    try:
        days = int(message.text.strip())
        if days <= 0 or days > 365:
            raise ValueError
    except ValueError:
        await message.answer("❌ Listing duration must be a number from 1 to 365.")
        return
    await state.update_data(listing_duration_days=days)
    await state.set_state(AddBankStates.waiting_stock_count)
    await message.answer(
        "📦 Enter stock quantity for this bank:\n\n"
        "Send a positive number. If you send 0, the bank will be saved as out of stock.",
    )


@router.message(AddBankStates.waiting_stock_count, F.text)
async def add_bank_stock_count(message: Message, state: FSMContext, session: AsyncSession, seller, **kwargs):
    try:
        stock_count = int(message.text.strip())
        if stock_count < 0 or stock_count > 1000:
            raise ValueError
    except ValueError:
        await message.answer("❌ Quantity must be a number from 0 to 1000.")
        return

    data = await state.get_data()
    await state.update_data(stock_count=stock_count)
    await state.set_state(AddBankStates.confirmation)
    upload_mode = "bulk" if stock_count > 1 else "single"
    await message.answer(
        f"📋 <b>Review bank upload</b>\n\n"
        f"🏦 {data['bank_name']}\n"
        f"🧩 Product: {bank_item_badge(data.get('product_type', 'bank'), data.get('product_subtype', 'log'))}\n"
        f"🔑 Code: {data.get('bank_code') or 'auto'}\n"
        f"📂 Category: {data['category']}\n"
        f"💰 Your price: ${Decimal(str(data['seller_price'])):.2f}\n"
        f"🛒 Final buyer price: set by moderation\n"
        f"💬 Support chat: {'Enabled' if data.get('has_chat', True) else 'Disabled'}\n"
        f"📱 Number access: {'Yes' if data.get('number_access_available') else 'No'}\n"
        f"📆 Rental days: {data.get('rental_days') or '-'}\n"
        f"🔁 Number change allowed: {'Yes' if data.get('number_change_allowed') else 'No'}\n"
        f"🗺 State: {data.get('state') or '-'}\n"
        f"📮 ZIP: {data.get('zip') or '-'}\n"
        f"🔐 Portal: {data.get('portal') or '-'}\n"
        f"💳 Card type: {data.get('card_type') or '-'}\n"
        f"🪪 SSN: {'Yes' if data.get('has_ssn') else 'No'}\n"
        f"📄 Docs: {'Yes' if data.get('has_docs') else 'No'}\n"
        f"📄 Doc type: {data.get('doc_type') or '-'}\n"
        f"📋 Log details: {'Attached' if data.get('details_text') else '-'}\n"
        f"⏳ Auto-unpublish days: {data.get('listing_duration_days') or '-'}\n"
        f"📦 Quantity: {stock_count}\n"
        f"🗂 Upload mode: {upload_mode}\n"
        f"📝 Description: {data.get('description') or '-'}\n"
        f"📘 Instruction: {data.get('instruction') or '-'}\n\n"
        f"After submit this will create a moderation batch and appear in My Uploads.",
        reply_markup=_bank_submit_keyboard(),
    )


@router.callback_query(F.data == "seller_bank_submit_confirm", AddBankStates.confirmation)
async def submit_bank_upload(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, **kwargs):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    data = await state.get_data()
    try:
        batch, bank, _summary = await SellerUploadPipelineService.create_bank_batch(
            session,
            seller_id=seller.id,
            payload={
                "bank_name": data["bank_name"],
                "bank_code": data.get("bank_code"),
                "category": data["category"],
                "product_type": data.get("product_type", "bank"),
                "product_subtype": data.get("product_subtype", "log"),
                "seller_price": data["seller_price"],
                "description": data.get("description"),
                "instruction": data.get("instruction"),
                "stock_count": data["stock_count"],
                "has_chat": data.get("has_chat", True),
                "number_access_available": data.get("number_access_available", False),
                "rental_days": data.get("rental_days"),
                "adaptive_report_enabled": data.get("adaptive_report_enabled", False),
                "number_change_allowed": data.get("number_change_allowed", False),
                "auto_unpublish_enabled": data.get("auto_unpublish_enabled", False),
                "listing_duration_days": data.get("listing_duration_days"),
                "state": data.get("state"),
                "zip": data.get("zip"),
                "portal": data.get("portal"),
                "card_type": data.get("card_type"),
                "has_ssn": data.get("has_ssn", False),
                "has_dob": data.get("has_dob", False),
                "has_name": data.get("has_name", False),
                "has_address": data.get("has_address", False),
                "has_email": data.get("has_email", False),
                "has_security_qa": data.get("has_security_qa", False),
                "has_docs": data.get("has_docs", False),
                "doc_type": data.get("doc_type"),
                "phone_area_code": data.get("phone_area_code"),
                "details_text": data.get("details_text"),
            },
        )
    except ValueError as exc:
        NocoDBService.log_seller_upload(
            seller_id=seller.id,
            category=data.get("category"),
            status="failed",
            error_reason=str(exc),
            extra={
                "item_type": "bank",
                "bank_name": data.get("bank_name"),
                "product_type": data.get("product_type", "bank"),
                "product_subtype": data.get("product_subtype", "log"),
            },
        )
        await callback.answer(str(exc), show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        f"✅ <b>Bank upload submitted!</b>\n\n"
        f"🏦 {bank.bank_name}\n"
        f"🧩 Product: {bank_item_badge(getattr(bank, 'product_type', 'bank'), getattr(bank, 'product_subtype', 'log'))}\n"
        f"📂 Category: {bank.category}\n"
        f"💰 Your price: ${bank.seller_price:.2f}\n"
        f"🛒 Final price: ${bank.buyer_price:.2f}\n"
        f"💬 Support chat: {'Enabled' if bank.has_chat else 'Disabled'}\n"
        f"📦 Batch: #{batch.id} ({batch.upload_mode})\n"
        f"📦 Quantity: {bank.stock_count}\n"
        f"🟡 Moderation: {bank.moderation_status}\n"
        f"You can track the batch in <b>My Uploads</b>.",
        reply_markup=seller_bank_detail(bank.id, bank.is_in_stock),
    )
    await callback.answer("Upload submitted", show_alert=True)


@router.callback_query(F.data.startswith("seller_bank:"))
async def bank_detail_handler(callback: CallbackQuery, session: AsyncSession, seller, **kwargs):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    
    bank_id = int(callback.data.split(":")[1])
    bank = await StockService.get_bank_by_id(session, bank_id)
    
    if not bank or bank.seller_id != seller.id:
        await callback.answer("❌ Bank not found", show_alert=True)
        return
    
    stock_text = "✅ In Stock" if bank.is_in_stock else "❌ Out of Stock"
    free_stock = max(0, int(bank.stock_count or 0) - int(getattr(bank, "reserved_count", 0) or 0))
    desc_text = f"\n📝 {bank.description}" if bank.description else ""
    instr_text = f"\n📘 {bank.instruction}" if getattr(bank, "instruction", None) else ""
    
    await callback.message.edit_text(
        f"🏦 <b>{bank.bank_name}</b>\n\n"
        f"🧩 Product: {bank_item_badge(getattr(bank, 'product_type', 'bank'), getattr(bank, 'product_subtype', 'log'))}\n"
        f"📂 Category: {bank.category}\n"
        f"💰 Your price: ${bank.seller_price:.2f}\n"
        f"🛒 Final price: ${bank.buyer_price:.2f}\n"
        f"💬 Support chat: {'Enabled' if bank.has_chat else 'Disabled'}\n"
        f"📦 Quantity: {bank.stock_count}\n"
        f"🔒 Reserved: {getattr(bank, 'reserved_count', 0) or 0}\n"
        f"📭 Free stock: {free_stock}\n"
        f"🟡 Moderation: {bank.moderation_status}\n"
        f"🗂 Batch: #{bank.upload_batch_id or '-'}\n"
        f"📊 Status: {stock_text}"
        f"{f'<br>📝 Moderation note: {bank.moderation_comment}' if bank.moderation_comment else ''}"
        f"{desc_text}"
        f"{instr_text}",
        reply_markup=seller_bank_detail(bank.id, bank.is_in_stock)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_toggle:"))
async def toggle_stock_handler(callback: CallbackQuery, session: AsyncSession, seller, **kwargs):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    
    bank_id = int(callback.data.split(":")[1])
    bank = await StockService.get_bank_by_id(session, bank_id)
    
    if not bank or bank.seller_id != seller.id:
        await callback.answer("❌ Bank not found", show_alert=True)
        return
    
    bank = await StockService.toggle_stock(session, bank_id)
    
    status = "✅ In Stock" if bank.is_in_stock else "❌ Out of Stock"
    await callback.answer(f"Updated: {status}", show_alert=True)
    
    free_stock = max(0, int(bank.stock_count or 0) - int(getattr(bank, "reserved_count", 0) or 0))
    desc_text = f"\n📝 {bank.description}" if bank.description else ""
    instr_text = f"\n📘 {bank.instruction}" if getattr(bank, "instruction", None) else ""
    await callback.message.edit_text(
        f"🏦 <b>{bank.bank_name}</b>\n\n"
        f"🧩 Product: {bank_item_badge(getattr(bank, 'product_type', 'bank'), getattr(bank, 'product_subtype', 'log'))}\n"
        f"📂 Category: {bank.category}\n"
        f"💰 Your price: ${bank.seller_price:.2f}\n"
        f"🛒 Final price: ${bank.buyer_price:.2f}\n"
        f"📦 Quantity: {bank.stock_count}\n"
        f"🔒 Reserved: {getattr(bank, 'reserved_count', 0) or 0}\n"
        f"📭 Free stock: {free_stock}\n"
        f"📊 Status: {status}"
        f"{desc_text}"
        f"{instr_text}",
        reply_markup=seller_bank_detail(bank.id, bank.is_in_stock)
    )


@router.callback_query(F.data.startswith("seller_qty:"))
async def change_qty_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, **kwargs):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return

    bank_id = int(callback.data.split(":")[1])
    bank = await StockService.get_bank_by_id(session, bank_id)
    if not bank or bank.seller_id != seller.id:
        await callback.answer("❌ Bank not found", show_alert=True)
        return

    await state.set_state(EditQtyStates.waiting_new_qty)
    await state.update_data(bank_id=bank_id)
    await callback.message.edit_text(
        f"📦 <b>Change Quantity for {bank.bank_name}</b>\n\n"
        f"Current quantity: {bank.stock_count}\n"
        f"Current status: {'✅ In Stock' if bank.is_in_stock else '❌ Out of Stock'}\n\n"
        f"Enter the new quantity:",
    )
    await callback.answer()


@router.message(EditQtyStates.waiting_new_qty, F.text)
async def change_qty_input(message: Message, state: FSMContext, session: AsyncSession, seller, **kwargs):
    try:
        new_qty = int(message.text.strip())
        if new_qty < 0 or new_qty > 1000:
            raise ValueError
    except ValueError:
        await message.answer("❌ Quantity must be a number from 0 to 1000.")
        return

    data = await state.get_data()
    bank_id = data["bank_id"]
    await state.clear()
    bank = await StockService.update_stock_count(session, bank_id, new_qty)
    if not bank:
        await message.answer("❌ Bank not found.")
        return

    await message.answer(
        f"✅ <b>Quantity updated!</b>\n\n"
        f"🏦 {bank.bank_name}\n"
        f"📦 Quantity: {bank.stock_count}\n"
        f"📊 Status: {'✅ In Stock' if bank.is_in_stock else '❌ Out of Stock'}",
        reply_markup=seller_bank_detail(bank.id, bank.is_in_stock),
    )


@router.callback_query(F.data.startswith("seller_price:"))
async def change_price_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, **kwargs):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    
    bank_id = int(callback.data.split(":")[1])
    bank = await StockService.get_bank_by_id(session, bank_id)
    
    if not bank or bank.seller_id != seller.id:
        await callback.answer("❌ Bank not found", show_alert=True)
        return
    
    await state.set_state(EditPriceStates.waiting_new_price)
    await state.update_data(bank_id=bank_id)
    
    await callback.message.edit_text(
        f"💰 <b>Change Price for {bank.bank_name}</b>\n\n"
        f"Current price: ${bank.seller_price:.2f}\n"
        f"Current final price: ${bank.buyer_price:.2f}\n\n"
        f"Enter the new <b>base price</b> in USD.\n"
        f"This will send the item back to moderation:"
    )
    await callback.answer()


@router.message(EditPriceStates.waiting_new_price, F.text)
async def change_price_input(message: Message, state: FSMContext, session: AsyncSession, seller, **kwargs):
    try:
        new_price = Decimal(message.text.strip().replace("$", "").replace(",", "."))
        if new_price <= 0 or new_price > 50000:
            await message.answer("❌ Price must be between $0.01 and $50,000:")
            return
    except (InvalidOperation, ValueError):
        await message.answer("❌ Invalid price. Enter a number:")
        return
    
    data = await state.get_data()
    bank_id = data["bank_id"]
    await state.clear()
    
    bank = await StockService.update_price(session, bank_id, new_price)
    
    if not bank:
        await message.answer("❌ Bank not found.")
        return
    
    await message.answer(
        f"✅ <b>Price updated!</b>\n\n"
        f"🏦 {bank.bank_name}\n"
        f"💰 New base price: ${bank.seller_price:.2f}\n"
        f"📊 Status: ⏳ Pending moderation",
        reply_markup=seller_bank_detail(bank.id, bank.is_in_stock)
    )


@router.callback_query(F.data.startswith("seller_delete:"))
async def delete_bank_confirm(callback: CallbackQuery, session: AsyncSession, seller, **kwargs):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    
    bank_id = int(callback.data.split(":")[1])
    bank = await StockService.get_bank_by_id(session, bank_id)
    
    if not bank or bank.seller_id != seller.id:
        await callback.answer("❌ Bank not found", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"🗑 <b>Delete {bank.bank_name}?</b>\n\n"
        f"This action cannot be undone.",
        reply_markup=confirm_delete_keyboard(bank_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_confirm_del:"))
async def delete_bank_execute(callback: CallbackQuery, session: AsyncSession, seller, **kwargs):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    
    bank_id = int(callback.data.split(":")[1])
    bank = await StockService.get_bank_by_id(session, bank_id)
    
    if not bank or bank.seller_id != seller.id:
        await callback.answer("❌ Bank not found", show_alert=True)
        return
    
    await StockService.delete_bank(session, bank_id)
    
    await callback.answer("✅ Bank deleted!", show_alert=True)
    
    banks = await StockService.get_seller_banks(session, seller.id)
    in_stock = sum(1 for b in banks if b.is_in_stock)
    total_qty = sum(max(0, int(getattr(b, "stock_count", 0) or 0)) for b in banks)
    
    await callback.message.edit_text(
        f"🏦 <b>My Banks</b> ({len(banks)} total)\n\n"
        f"✅ In stock: {in_stock}\n"
        f"❌ Out of stock: {len(banks) - in_stock}\n"
        f"📦 Total quantity: {total_qty}",
        reply_markup=seller_bank_list(banks)
    )
