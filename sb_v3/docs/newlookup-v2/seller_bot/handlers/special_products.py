from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from seller_bot.services.special_stock_service import SpecialStockService
from shared.database.models import EnrollCategory, EnrollCategoryRequest, SelfregCCCategory, SelfregCCCategoryRequest, BankTypeRequest
from shared.services.seller_deposit_service import SellerDepositService
from shared.services.seller_upload_batch_service import SellerUploadBatchService

router = Router(name="seller_special_products")


def _cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")],
    ])


def _yes_no_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Yes", callback_data=f"{prefix}:yes"),
            InlineKeyboardButton(text="❌ No", callback_data=f"{prefix}:no"),
        ],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")],
    ])


def _nfc_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍎 Apple Pay", callback_data="seller_nfc_type:ap")],
        [InlineKeyboardButton(text="🤖 Google Pay", callback_data="seller_nfc_type:gp")],
        [InlineKeyboardButton(text="📎 Other", callback_data="seller_nfc_type:other")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")],
    ])


def _sms_access_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Via Me (Seller)", callback_data="seller_otp_sms:seller_mediated")],
        [InlineKeyboardButton(text="🔓 Direct Account Access", callback_data="seller_otp_sms:account_access")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")],
    ])


def _check_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Personal", callback_data="seller_check_type:personal")],
        [InlineKeyboardButton(text="Business", callback_data="seller_check_type:business")],
        [InlineKeyboardButton(text="Payroll", callback_data="seller_check_type:payroll")],
        [InlineKeyboardButton(text="Cashier", callback_data="seller_check_type:cashier")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")],
    ])


ENROLL_REQ_CODE = "__request__"
SELFREG_CC_REQ_CODE = "__request__"


def _enroll_card_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Credit", callback_data="seller_enroll_card:credit")],
        [InlineKeyboardButton(text="💳 Debit", callback_data="seller_enroll_card:debit")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")],
    ])


def _nfc_label(nfc_type: str) -> str:
    if nfc_type == "ap":
        return "Apple Pay"
    if nfc_type == "gp":
        return "Google Pay"
    if nfc_type == "other":
        return "Other NFC"
    return nfc_type.upper()


def _nfc_subtype(nfc_type: str) -> str:
    if nfc_type == "ap":
        return "apple_pay"
    if nfc_type == "gp":
        return "google_pay"
    return "other"


def _parse_price(text: str) -> Decimal | None:
    try:
        value = Decimal(text.strip().replace("$", "").replace(",", "."))
    except (InvalidOperation, ValueError):
        return None
    if value <= 0:
        return None
    return value


async def _t(ui_texts, key: str, default: str, **fmt) -> str:
    return await ui_texts.get(key, default, **fmt)


class AddNFCStates(StatesGroup):
    waiting_type = State()
    waiting_bank_name = State()
    waiting_country = State()
    waiting_state = State()
    waiting_zip = State()
    waiting_price = State()
    waiting_file = State()


class AddOTPStates(StatesGroup):
    waiting_bank_name = State()
    waiting_balance = State()
    waiting_has_fullz = State()
    waiting_sms_access = State()
    waiting_price = State()


class AddSelfregCCStates(StatesGroup):
    waiting_category = State()
    waiting_request_name = State()
    waiting_bank_name = State()
    waiting_card_name = State()
    waiting_credit_limit = State()
    waiting_vcc_limit = State()
    waiting_state = State()
    waiting_zip = State()
    waiting_has_email = State()
    waiting_has_phone = State()
    waiting_phone_days = State()
    waiting_phone_renewable = State()
    waiting_phone_change_allowed = State()
    waiting_online_access = State()
    waiting_price = State()


class AddCheckStates(StatesGroup):
    waiting_check_type = State()
    waiting_bank_name = State()
    waiting_amount = State()
    waiting_state = State()
    waiting_price = State()
    waiting_scan = State()


class AddEnrollStates(StatesGroup):
    waiting_request_name = State()
    waiting_bank_name = State()
    waiting_balance = State()
    waiting_zip = State()
    waiting_state_field = State()
    waiting_price = State()
    waiting_card_type = State()


def _ensure_upload_access(callback_or_message, seller, seller_actor, package_code: str) -> str | None:
    if not seller or not seller_actor or not seller_actor.can_upload():
        return "❌ Not authorized"
    if not SellerDepositService.has_upload_access(seller, package_code):
        return f"❌ {package_code.upper()} package deposit is required before upload."
    return None


@router.callback_query(F.data == "seller_add_nfc")
async def add_nfc_start(callback: CallbackQuery, state: FSMContext, seller, ui_texts, **kwargs):
    error = _ensure_upload_access(callback, seller, kwargs.get("seller_actor"), "bank")
    if error:
        await callback.answer(error, show_alert=True)
        return
    await state.clear()
    await state.set_state(AddNFCStates.waiting_type)
    await callback.message.edit_text(
        await _t(ui_texts, "seller.nfc.start", "Add NFC item.\n\nSelect NFC type:"),
        reply_markup=_nfc_type_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_nfc_type:"), AddNFCStates.waiting_type)
async def add_nfc_type(callback: CallbackQuery, state: FSMContext, ui_texts):
    nfc_type = callback.data.split(":")[1]
    await state.update_data(nfc_type=nfc_type)
    await state.set_state(AddNFCStates.waiting_bank_name)
    await callback.message.edit_text(
        await _t(ui_texts, "seller.nfc.bank", "Enter bank name:"),
        reply_markup=_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AddNFCStates.waiting_bank_name, F.text)
async def add_nfc_bank_name(message: Message, state: FSMContext, ui_texts):
    await state.update_data(bank_name=message.text.strip())
    await state.set_state(AddNFCStates.waiting_country)
    await message.answer(await _t(ui_texts, "seller.nfc.country", "Enter country code (example: US):"))


@router.message(AddNFCStates.waiting_country, F.text)
async def add_nfc_country(message: Message, state: FSMContext, ui_texts):
    await state.update_data(country=message.text.strip().upper())
    await state.set_state(AddNFCStates.waiting_state)
    await message.answer(await _t(ui_texts, "seller.nfc.state", "Enter state (or - to skip):"))


@router.message(AddNFCStates.waiting_state, F.text)
async def add_nfc_state(message: Message, state: FSMContext, ui_texts):
    await state.update_data(state=None if message.text.strip() == "-" else message.text.strip())
    await state.set_state(AddNFCStates.waiting_zip)
    await message.answer(await _t(ui_texts, "seller.nfc.zip", "Enter ZIP (or - to skip):"))


@router.message(AddNFCStates.waiting_zip, F.text)
async def add_nfc_zip(message: Message, state: FSMContext, ui_texts):
    await state.update_data(zip=None if message.text.strip() == "-" else message.text.strip())
    await state.set_state(AddNFCStates.waiting_price)
    await message.answer(await _t(ui_texts, "seller.nfc.price", "Enter your base price in USD:"))


@router.message(AddNFCStates.waiting_price, F.text)
async def add_nfc_price(message: Message, state: FSMContext, ui_texts):
    price = _parse_price(message.text)
    if price is None:
        await message.answer(await _t(ui_texts, "seller.common.invalid_price", "Invalid price. Enter a positive number."))
        return
    await state.update_data(seller_price=str(price))
    await state.set_state(AddNFCStates.waiting_file)
    await message.answer(await _t(ui_texts, "seller.nfc.file", "Upload the .txt or .zip file with NFC data."))


@router.message(AddNFCStates.waiting_file, F.document)
async def add_nfc_file(message: Message, state: FSMContext, session: AsyncSession, seller, ui_texts, **kwargs):
    data = await state.get_data()
    batch = await SellerUploadBatchService.create_batch(
        session,
        seller_id=seller.id,
        item_type="nfc",
        upload_mode="single",
        title=f"{data['bank_name']} {data['nfc_type'].upper()}",
        total_items=1,
    )
    item = await SpecialStockService.add_nfc_item(
        session,
        seller_id=seller.id,
        upload_batch_id=batch.id,
        item_name=f"{_nfc_label(data['nfc_type'])} | {data['bank_name']}",
        nfc_type=data["nfc_type"],
        product_subtype=_nfc_subtype(data["nfc_type"]),
        bank_name=data["bank_name"],
        country=data["country"],
        state=data.get("state"),
        zip=data.get("zip"),
        seller_price=Decimal(str(data["seller_price"])),
        base_price=Decimal(str(data["seller_price"])),
        buyer_price=Decimal(str(data["seller_price"])),
        data_file_path=message.document.file_id,
        moderation_status="pending_moderation",
        is_in_stock=True,
        is_active=True,
    )
    await state.clear()
    await message.answer(
        await _t(ui_texts, "seller.nfc.created", "NFC item submitted for moderation.\n\nItem: {item_name}\nBatch: #{batch_id}", item_name=item.item_name, batch_id=batch.id)
    )


@router.callback_query(F.data == "seller_add_otp")
async def add_otp_start(callback: CallbackQuery, state: FSMContext, seller, ui_texts, **kwargs):
    error = _ensure_upload_access(callback, seller, kwargs.get("seller_actor"), "bank")
    if error:
        await callback.answer(error, show_alert=True)
        return
    await state.clear()
    await state.set_state(AddOTPStates.waiting_bank_name)
    await callback.message.edit_text(await _t(ui_texts, "seller.otp.bank", "Enter bank name:"), reply_markup=_cancel_keyboard())
    await callback.answer()


@router.message(AddOTPStates.waiting_bank_name, F.text)
async def add_otp_bank_name(message: Message, state: FSMContext, ui_texts):
    await state.update_data(bank_name=message.text.strip())
    await state.set_state(AddOTPStates.waiting_balance)
    await message.answer(await _t(ui_texts, "seller.otp.balance", "Enter balance amount:"))


@router.message(AddOTPStates.waiting_balance, F.text)
async def add_otp_balance(message: Message, state: FSMContext, ui_texts):
    balance = _parse_price(message.text)
    if balance is None:
        await message.answer(await _t(ui_texts, "seller.common.invalid_balance", "Invalid balance. Enter a positive number."))
        return
    await state.update_data(balance=str(balance))
    await state.set_state(AddOTPStates.waiting_has_fullz)
    await message.answer(await _t(ui_texts, "seller.otp.fullz", "Fullz included?"), reply_markup=_yes_no_keyboard("seller_otp_fullz"))


@router.callback_query(F.data.startswith("seller_otp_fullz:"), AddOTPStates.waiting_has_fullz)
async def add_otp_has_fullz(callback: CallbackQuery, state: FSMContext, ui_texts):
    await state.update_data(has_fullz=callback.data.split(":")[1] == "yes")
    await state.set_state(AddOTPStates.waiting_sms_access)
    await callback.message.edit_text(await _t(ui_texts, "seller.otp.sms_access", "Select SMS access method:"), reply_markup=_sms_access_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("seller_otp_sms:"), AddOTPStates.waiting_sms_access)
async def add_otp_sms_access(callback: CallbackQuery, state: FSMContext, ui_texts):
    await state.update_data(sms_access_type=callback.data.split(":")[1])
    await state.set_state(AddOTPStates.waiting_price)
    await callback.message.edit_text(await _t(ui_texts, "seller.otp.price", "Enter your base price in USD:"), reply_markup=_cancel_keyboard())
    await callback.answer()


@router.message(AddOTPStates.waiting_price, F.text)
async def add_otp_price(message: Message, state: FSMContext, session: AsyncSession, seller, ui_texts):
    price = _parse_price(message.text)
    if price is None:
        await message.answer(await _t(ui_texts, "seller.common.invalid_price", "Invalid price. Enter a positive number."))
        return
    data = await state.get_data()
    batch = await SellerUploadBatchService.create_batch(
        session,
        seller_id=seller.id,
        item_type="otp",
        upload_mode="single",
        title=f"OTP | {data['bank_name']}",
        total_items=1,
    )
    item = await SpecialStockService.add_otp_item(
        session,
        seller_id=seller.id,
        upload_batch_id=batch.id,
        item_name=f"OTP | {data['bank_name']} | ${Decimal(str(data['balance'])):.0f}",
        bank_name=data["bank_name"],
        balance=Decimal(str(data["balance"])),
        has_fullz=bool(data.get("has_fullz")),
        sms_access_type=data["sms_access_type"],
        seller_price=price,
        base_price=price,
        buyer_price=price,
        moderation_status="pending_moderation",
        is_in_stock=True,
        is_active=True,
    )
    await state.clear()
    await message.answer(
        await _t(ui_texts, "seller.otp.created", "OTP item submitted for moderation.\n\nItem: {item_name}\nBatch: #{batch_id}", item_name=item.item_name, batch_id=batch.id)
    )


@router.callback_query(F.data == "seller_add_enroll")
async def add_enroll_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, ui_texts, **kwargs):
    error = _ensure_upload_access(callback, seller, kwargs.get("seller_actor"), "bank")
    if error:
        await callback.answer(error, show_alert=True)
        return
    await state.clear()
    result = await session.execute(
        select(EnrollCategory).where(EnrollCategory.is_active == True).order_by(
            EnrollCategory.position, EnrollCategory.id
        )
    )
    cats = list(result.scalars().all())
    if not cats:
        await callback.answer("No enroll categories configured yet.", show_alert=True)
        return
    rows = [
        [InlineKeyboardButton(text=c.name, callback_data=f"seller_enroll_cat:{c.code}")]
        for c in cats
    ]
    rows.append([InlineKeyboardButton(text="📝 Request new portal category", callback_data=f"seller_enroll_cat:{ENROLL_REQ_CODE}")])
    rows.append([InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")])
    await callback.message.edit_text(
        await _t(ui_texts, "seller.enroll.pick_category", "🏦 Add Enroll item.\n\nSelect portal category:"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_enroll_cat:"))
async def add_enroll_category_picked(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, ui_texts):
    _, code = callback.data.split(":", 1)
    if code == ENROLL_REQ_CODE:
        await state.set_state(AddEnrollStates.waiting_request_name)
        await callback.message.edit_text(
            await _t(
                ui_texts,
                "seller.enroll.request_name",
                "Enter the portal / category name you need.\n\n"
                "Our team will review within 1–6 hours. You cannot upload to this category until it is created.",
            ),
            reply_markup=_cancel_keyboard(),
        )
        await callback.answer()
        return
    cat = await session.scalar(
        select(EnrollCategory).where(EnrollCategory.code == code, EnrollCategory.is_active == True)
    )
    if not cat:
        await callback.answer("Category not found.", show_alert=True)
        return
    await state.update_data(enroll_category_id=cat.id, portal=cat.name)
    await state.set_state(AddEnrollStates.waiting_bank_name)
    await callback.message.edit_text(
        await _t(ui_texts, "seller.enroll.bank", "Enter bank name:"),
        reply_markup=_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AddEnrollStates.waiting_request_name, F.text)
async def add_enroll_request_name(message: Message, state: FSMContext, session: AsyncSession, seller, ui_texts):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Name too short. Try again.")
        return
    session.add(EnrollCategoryRequest(seller_id=seller.id, requested_name=name, status="pending"))
    await session.commit()
    await state.clear()
    await message.answer(
        await _t(
            ui_texts,
            "seller.enroll.request_submitted",
            "Request submitted. Our team will review within 1–6 hours. You will be notified when the category is available.",
        )
    )


@router.message(AddEnrollStates.waiting_bank_name, F.text)
async def add_enroll_bank_name(message: Message, state: FSMContext, ui_texts):
    await state.update_data(bank_name=message.text.strip())
    await state.set_state(AddEnrollStates.waiting_balance)
    await message.answer(await _t(ui_texts, "seller.enroll.balance", "Enter balance amount (USD):"))


@router.message(AddEnrollStates.waiting_balance, F.text)
async def add_enroll_balance(message: Message, state: FSMContext, ui_texts):
    bal = _parse_price(message.text)
    if bal is None:
        await message.answer(await _t(ui_texts, "seller.common.invalid_amount", "Invalid amount. Enter a positive number."))
        return
    await state.update_data(balance=str(bal))
    await state.set_state(AddEnrollStates.waiting_zip)
    await message.answer(await _t(ui_texts, "seller.enroll.zip", "Enter ZIP code:"))


@router.message(AddEnrollStates.waiting_zip, F.text)
async def add_enroll_zip(message: Message, state: FSMContext, ui_texts):
    await state.update_data(card_zip=message.text.strip())
    await state.set_state(AddEnrollStates.waiting_state_field)
    await message.answer(await _t(ui_texts, "seller.enroll.state", "Enter state (2-letter code):"))


@router.message(AddEnrollStates.waiting_state_field, F.text)
async def add_enroll_state(message: Message, state: FSMContext, ui_texts):
    await state.update_data(card_state=message.text.strip())
    await state.set_state(AddEnrollStates.waiting_price)
    await message.answer(await _t(ui_texts, "seller.enroll.price", "Enter your price in USD:"))


@router.message(AddEnrollStates.waiting_price, F.text)
async def add_enroll_price(message: Message, state: FSMContext, ui_texts):
    price = _parse_price(message.text)
    if price is None:
        await message.answer(await _t(ui_texts, "seller.common.invalid_price", "Invalid price. Enter a positive number."))
        return
    await state.update_data(price=str(price))
    await state.set_state(AddEnrollStates.waiting_card_type)
    await message.answer(
        await _t(ui_texts, "seller.enroll.card_type", "Card type:"),
        reply_markup=_enroll_card_type_keyboard(),
    )


@router.callback_query(F.data.startswith("seller_enroll_card:"), AddEnrollStates.waiting_card_type)
async def add_enroll_card_type(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, ui_texts):
    card_type = callback.data.split(":")[1]
    if card_type not in ("credit", "debit"):
        await callback.answer("Invalid type", show_alert=True)
        return
    data = await state.get_data()
    batch = await SellerUploadBatchService.create_batch(
        session,
        seller_id=seller.id,
        item_type="enroll",
        upload_mode="single",
        title=f"Enroll | {data.get('portal', '')}",
        total_items=1,
    )
    bal = float(Decimal(str(data["balance"])))
    pr = float(Decimal(str(data["price"])))
    await SpecialStockService.add_enroll_item(
        session,
        seller_id=seller.id,
        enroll_category_id=int(data["enroll_category_id"]),
        portal=data["portal"],
        bank_name=data["bank_name"],
        balance=bal,
        card_zip=data["card_zip"],
        card_state=data["card_state"],
        card_type=card_type,
        price=pr,
        moderation_status="pending_moderation",
        is_active=True,
        is_in_stock=True,
    )
    await state.clear()
    await callback.message.edit_text(
        await _t(
            ui_texts,
            "seller.enroll.created",
            "Enroll item submitted for moderation.\n\nPortal: {portal}\nBatch: #{batch_id}",
            portal=data.get("portal", ""),
            batch_id=batch.id,
        )
    )
    await callback.answer()


@router.callback_query(F.data == "seller_add_selfreg_cc")
async def add_selfreg_cc_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, ui_texts, **kwargs):
    error = _ensure_upload_access(callback, seller, kwargs.get("seller_actor"), "cc")
    if error:
        await callback.answer(error, show_alert=True)
        return
    await state.clear()
    result = await session.execute(
        select(SelfregCCCategory).where(SelfregCCCategory.is_active == True).order_by(
            SelfregCCCategory.position, SelfregCCCategory.id
        )
    )
    cats = list(result.scalars().all())
    if not cats:
        await callback.answer("No Selfreg CC categories configured yet.", show_alert=True)
        return
    rows = [
        [InlineKeyboardButton(text=c.name, callback_data=f"seller_selfreg_cc_cat:{c.code}")]
        for c in cats
    ]
    rows.append([InlineKeyboardButton(text="📝 Request new bank category", callback_data=f"seller_selfreg_cc_cat:{SELFREG_CC_REQ_CODE}")])
    rows.append([InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")])
    await callback.message.edit_text(
        await _t(ui_texts, "seller.selfreg_cc.pick_category", "💳 Add Selfreg CC item.\n\nSelect bank category:"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_selfreg_cc_cat:"))
async def add_selfreg_cc_category_picked(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, ui_texts):
    _, code = callback.data.split(":", 1)
    if code == SELFREG_CC_REQ_CODE:
        await state.set_state(AddSelfregCCStates.waiting_request_name)
        await callback.message.edit_text(
            await _t(
                ui_texts,
                "seller.selfreg_cc.request_name",
                "Enter the bank / category name you need.\n\n"
                "Our team will review within 1–6 hours. You cannot upload to this category until it is created.",
            ),
            reply_markup=_cancel_keyboard(),
        )
        await callback.answer()
        return
    cat = await session.scalar(
        select(SelfregCCCategory).where(SelfregCCCategory.code == code, SelfregCCCategory.is_active == True)
    )
    if not cat:
        await callback.answer("Category not found.", show_alert=True)
        return
    await state.update_data(selfreg_cc_category_id=cat.id, bank_name=cat.name)
    await state.set_state(AddSelfregCCStates.waiting_card_name)
    await callback.message.edit_text(
        await _t(ui_texts, "seller.selfreg_cc.card_name", f"Category: {cat.name}\n\nEnter card name/title:"),
        reply_markup=_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AddSelfregCCStates.waiting_request_name, F.text)
async def add_selfreg_cc_request_name(message: Message, state: FSMContext, session: AsyncSession, seller, ui_texts):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Name too short. Try again.")
        return
    session.add(SelfregCCCategoryRequest(seller_id=seller.id, requested_name=name, status="pending"))
    await session.commit()
    await state.clear()
    await message.answer(
        await _t(
            ui_texts,
            "seller.selfreg_cc.request_submitted",
            "Request submitted. Our team will review within 1–6 hours. You will be notified when the category is available.",
        )
    )


@router.message(AddSelfregCCStates.waiting_card_name, F.text)
async def add_selfreg_cc_card_name(message: Message, state: FSMContext, ui_texts):
    await state.update_data(card_name=message.text.strip())
    await state.set_state(AddSelfregCCStates.waiting_credit_limit)
    await message.answer(await _t(ui_texts, "seller.selfreg_cc.credit_limit", "Enter credit limit (or - to skip):"))


@router.message(AddSelfregCCStates.waiting_credit_limit, F.text)
async def add_selfreg_cc_credit_limit(message: Message, state: FSMContext, ui_texts):
    value = None if message.text.strip() == "-" else _parse_price(message.text)
    if message.text.strip() != "-" and value is None:
        await message.answer(await _t(ui_texts, "seller.common.invalid_amount", "Invalid amount. Enter a positive number or -."))
        return
    await state.update_data(credit_limit=str(value) if value is not None else None)
    await state.set_state(AddSelfregCCStates.waiting_vcc_limit)
    await message.answer(await _t(ui_texts, "seller.selfreg_cc.vcc_limit", "Enter VCC limit (or - to skip):"))


@router.message(AddSelfregCCStates.waiting_vcc_limit, F.text)
async def add_selfreg_cc_vcc_limit(message: Message, state: FSMContext, ui_texts):
    value = None if message.text.strip() == "-" else _parse_price(message.text)
    if message.text.strip() != "-" and value is None:
        await message.answer(await _t(ui_texts, "seller.common.invalid_amount", "Invalid amount. Enter a positive number or -."))
        return
    await state.update_data(vcc_limit=str(value) if value is not None else None)
    await state.set_state(AddSelfregCCStates.waiting_state)
    await message.answer(await _t(ui_texts, "seller.selfreg_cc.state", "Enter state:"))


@router.message(AddSelfregCCStates.waiting_state, F.text)
async def add_selfreg_cc_state(message: Message, state: FSMContext, ui_texts):
    await state.update_data(state=message.text.strip())
    await state.set_state(AddSelfregCCStates.waiting_zip)
    await message.answer(await _t(ui_texts, "seller.selfreg_cc.zip", "Enter ZIP:"))


@router.message(AddSelfregCCStates.waiting_zip, F.text)
async def add_selfreg_cc_zip(message: Message, state: FSMContext, ui_texts):
    await state.update_data(zip=message.text.strip())
    await state.set_state(AddSelfregCCStates.waiting_has_email)
    await message.answer(await _t(ui_texts, "seller.selfreg_cc.has_email", "Email access included?"), reply_markup=_yes_no_keyboard("seller_selfreg_cc_email"))


@router.callback_query(F.data.startswith("seller_selfreg_cc_email:"), AddSelfregCCStates.waiting_has_email)
async def add_selfreg_cc_has_email(callback: CallbackQuery, state: FSMContext, ui_texts):
    await state.update_data(has_email=callback.data.split(":")[1] == "yes")
    await state.set_state(AddSelfregCCStates.waiting_has_phone)
    await callback.message.edit_text(await _t(ui_texts, "seller.selfreg_cc.has_phone", "Phone access included?"), reply_markup=_yes_no_keyboard("seller_selfreg_cc_phone"))
    await callback.answer()


@router.callback_query(F.data.startswith("seller_selfreg_cc_phone:"), AddSelfregCCStates.waiting_has_phone)
async def add_selfreg_cc_has_phone(callback: CallbackQuery, state: FSMContext, ui_texts):
    has_phone = callback.data.split(":")[1] == "yes"
    await state.update_data(has_phone=has_phone)
    if has_phone:
        await state.set_state(AddSelfregCCStates.waiting_phone_days)
        await callback.message.edit_text(await _t(ui_texts, "seller.selfreg_cc.phone_days", "How many phone days remain?"), reply_markup=_cancel_keyboard())
    else:
        await state.update_data(phone_days_remaining=None, phone_renewable=None, phone_change_allowed=None)
        await state.set_state(AddSelfregCCStates.waiting_online_access)
        await callback.message.edit_text(await _t(ui_texts, "seller.selfreg_cc.online_access", "Online access available?"), reply_markup=_yes_no_keyboard("seller_selfreg_cc_online"))
    await callback.answer()


@router.message(AddSelfregCCStates.waiting_phone_days, F.text)
async def add_selfreg_cc_phone_days(message: Message, state: FSMContext, ui_texts):
    try:
        days = int(message.text.strip())
    except ValueError:
        await message.answer(await _t(ui_texts, "seller.common.invalid_days", "Invalid number of days."))
        return
    await state.update_data(phone_days_remaining=days)
    await state.set_state(AddSelfregCCStates.waiting_phone_renewable)
    await message.answer(await _t(ui_texts, "seller.selfreg_cc.phone_renewable", "Phone renewable?"), reply_markup=_yes_no_keyboard("seller_selfreg_cc_renewable"))


@router.callback_query(F.data.startswith("seller_selfreg_cc_renewable:"), AddSelfregCCStates.waiting_phone_renewable)
async def add_selfreg_cc_phone_renewable(callback: CallbackQuery, state: FSMContext, ui_texts):
    await state.update_data(phone_renewable=callback.data.split(":")[1] == "yes")
    await state.set_state(AddSelfregCCStates.waiting_phone_change_allowed)
    await callback.message.edit_text(await _t(ui_texts, "seller.selfreg_cc.phone_change", "Phone change allowed?"), reply_markup=_yes_no_keyboard("seller_selfreg_cc_change"))
    await callback.answer()


@router.callback_query(F.data.startswith("seller_selfreg_cc_change:"), AddSelfregCCStates.waiting_phone_change_allowed)
async def add_selfreg_cc_phone_change(callback: CallbackQuery, state: FSMContext, ui_texts):
    await state.update_data(phone_change_allowed=callback.data.split(":")[1] == "yes")
    await state.set_state(AddSelfregCCStates.waiting_online_access)
    await callback.message.edit_text(await _t(ui_texts, "seller.selfreg_cc.online_access", "Online access available?"), reply_markup=_yes_no_keyboard("seller_selfreg_cc_online"))
    await callback.answer()


@router.callback_query(F.data.startswith("seller_selfreg_cc_online:"), AddSelfregCCStates.waiting_online_access)
async def add_selfreg_cc_online(callback: CallbackQuery, state: FSMContext, ui_texts):
    await state.update_data(online_access=callback.data.split(":")[1] == "yes")
    await state.set_state(AddSelfregCCStates.waiting_price)
    await callback.message.edit_text(await _t(ui_texts, "seller.selfreg_cc.price", "Enter your base price in USD:"), reply_markup=_cancel_keyboard())
    await callback.answer()


@router.message(AddSelfregCCStates.waiting_price, F.text)
async def add_selfreg_cc_price(message: Message, state: FSMContext, session: AsyncSession, seller, ui_texts):
    price = _parse_price(message.text)
    if price is None:
        await message.answer(await _t(ui_texts, "seller.common.invalid_price", "Invalid price. Enter a positive number."))
        return
    data = await state.get_data()
    batch = await SellerUploadBatchService.create_batch(
        session,
        seller_id=seller.id,
        item_type="selfreg_cc",
        upload_mode="single",
        title=f"{data['bank_name']} selfreg cc",
        total_items=1,
    )
    item = await SpecialStockService.add_selfreg_cc_item(
        session,
        seller_id=seller.id,
        upload_batch_id=batch.id,
        selfreg_cc_category_id=data.get("selfreg_cc_category_id"),
        item_name=f"{data['bank_name']} — {data.get('card_name') or 'Selfreg CC'}",
        bank_name=data["bank_name"],
        card_name=data.get("card_name"),
        credit_limit=Decimal(str(data["credit_limit"])) if data.get("credit_limit") else None,
        vcc_limit=Decimal(str(data["vcc_limit"])) if data.get("vcc_limit") else None,
        state=data.get("state"),
        zip=data.get("zip"),
        has_email=bool(data.get("has_email")),
        has_phone=bool(data.get("has_phone")),
        phone_days_remaining=data.get("phone_days_remaining"),
        phone_renewable=data.get("phone_renewable"),
        phone_change_allowed=data.get("phone_change_allowed"),
        online_access=bool(data.get("online_access")),
        seller_price=price,
        base_price=price,
        buyer_price=price,
        moderation_status="pending_moderation",
        is_in_stock=True,
        is_active=True,
    )
    await state.clear()
    await message.answer(
        await _t(ui_texts, "seller.selfreg_cc.created", "Selfreg CC item submitted for moderation.\n\nItem: {item_name}\nBatch: #{batch_id}", item_name=item.item_name, batch_id=batch.id)
    )


@router.callback_query(F.data == "seller_add_check")
async def add_check_start(callback: CallbackQuery, state: FSMContext, seller, ui_texts, **kwargs):
    error = _ensure_upload_access(callback, seller, kwargs.get("seller_actor"), "bank")
    if error:
        await callback.answer(error, show_alert=True)
        return
    await state.clear()
    await state.set_state(AddCheckStates.waiting_check_type)
    await callback.message.edit_text(await _t(ui_texts, "seller.check.type", "Select check type:"), reply_markup=_check_type_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("seller_check_type:"), AddCheckStates.waiting_check_type)
async def add_check_type(callback: CallbackQuery, state: FSMContext, ui_texts):
    await state.update_data(check_type=callback.data.split(":")[1])
    await state.set_state(AddCheckStates.waiting_bank_name)
    await callback.message.edit_text(await _t(ui_texts, "seller.check.bank", "Enter bank name:"), reply_markup=_cancel_keyboard())
    await callback.answer()


@router.message(AddCheckStates.waiting_bank_name, F.text)
async def add_check_bank_name(message: Message, state: FSMContext, ui_texts):
    await state.update_data(bank_name=message.text.strip())
    await state.set_state(AddCheckStates.waiting_amount)
    await message.answer(await _t(ui_texts, "seller.check.amount", "Enter check amount:"))


@router.message(AddCheckStates.waiting_amount, F.text)
async def add_check_amount(message: Message, state: FSMContext, ui_texts):
    amount = _parse_price(message.text)
    if amount is None:
        await message.answer(await _t(ui_texts, "seller.common.invalid_amount", "Invalid amount. Enter a positive number."))
        return
    await state.update_data(amount=str(amount))
    await state.set_state(AddCheckStates.waiting_state)
    await message.answer(await _t(ui_texts, "seller.check.state", "Enter state (2-letter code):"))


@router.message(AddCheckStates.waiting_state, F.text)
async def add_check_state(message: Message, state: FSMContext, ui_texts):
    await state.update_data(state=message.text.strip())
    await state.set_state(AddCheckStates.waiting_price)
    await message.answer(await _t(ui_texts, "seller.check.price", "Enter your base price in USD:"))


@router.message(AddCheckStates.waiting_price, F.text)
async def add_check_price(message: Message, state: FSMContext, ui_texts):
    price = _parse_price(message.text)
    if price is None:
        await message.answer(await _t(ui_texts, "seller.common.invalid_price", "Invalid price. Enter a positive number."))
        return
    await state.update_data(seller_price=str(price))
    await state.set_state(AddCheckStates.waiting_scan)
    await message.answer(await _t(ui_texts, "seller.check.scan", "Upload scan image or document. This step is mandatory."))


@router.message(AddCheckStates.waiting_scan, F.photo | F.document)
async def add_check_scan(message: Message, state: FSMContext, session: AsyncSession, seller, ui_texts):
    data = await state.get_data()
    file_id = message.document.file_id if message.document else message.photo[-1].file_id
    batch = await SellerUploadBatchService.create_batch(
        session,
        seller_id=seller.id,
        item_type="check",
        upload_mode="single",
        title=f"{data['bank_name']} {data['check_type']}",
        total_items=1,
    )
    item = await SpecialStockService.add_check_item(
        session,
        seller_id=seller.id,
        upload_batch_id=batch.id,
        item_name=f"{data['check_type'].title()} | ${Decimal(str(data['amount'])):.0f} | {data['state']}",
        check_type=data["check_type"],
        bank_name=data["bank_name"],
        amount=Decimal(str(data["amount"])),
        state=data["state"],
        zip=None,
        has_holder_name=False,
        has_address=False,
        check_date=None,
        seller_description=None,
        scan_file_path=file_id,
        seller_price=Decimal(str(data["seller_price"])),
        base_price=Decimal(str(data["seller_price"])),
        buyer_price=Decimal(str(data["seller_price"])),
        moderation_status="pending_moderation",
        is_in_stock=True,
        is_active=True,
    )
    await state.clear()
    await message.answer(
        await _t(ui_texts, "seller.check.created", "Check item submitted for moderation.\n\nItem: {item_name}\nBatch: #{batch_id}", item_name=item.item_name, batch_id=batch.id)
    )
