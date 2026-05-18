from __future__ import annotations

"""
Seller Bot — Brute Bank upload flow.
Селлер загружает брутованные банковские аккаунты шаг за шагом:
банк → credentials → баланс/описание → цена → submit.
"""

import logging
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.brute_bank_group_key import make_brute_group_key
from shared.database.models import BruteBankGroup, BruteBankItem
from shared.services.seller_deposit_service import SellerDepositService
from shared.services.nocodb_service import NocoDBService
from shared.services.seller_upload_pipeline_service import SellerUploadPipelineService

logger = logging.getLogger(__name__)
router = Router(name="seller_brute_bank")

class BruteUploadStates(StatesGroup):
    waiting_upload_mode = State()
    waiting_bank_name = State()
    waiting_request_bank_name = State()  # for request flow
    waiting_request_bank_code = State()
    waiting_request_attributes = State()
    waiting_request_category = State()
    waiting_bank_code = State()
    waiting_attributes = State()
    waiting_bulk_price = State()
    waiting_balance_range = State()
    waiting_account_type = State()
    waiting_bulk_items = State()
    waiting_credentials = State()
    waiting_balance = State()
    waiting_price = State()
    confirmation = State()

def _confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Submit for Review", callback_data="brute_submit")],
        [InlineKeyboardButton(text="✏️ Edit", callback_data="brute_restart")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="brute_cancel")],
    ])


def _upload_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ Single item", callback_data="brute_mode:single")],
        [InlineKeyboardButton(text="📦 Bulk upload", callback_data="brute_mode:bulk")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="brute_cancel")],
    ])


def _parse_bulk_brute_line(line: str) -> dict | None:
    parts = [p.strip() for p in line.split("|")]
    if len(parts) < 4:
        return None
    return {
        "credentials": {
            "login": parts[0],
            "password": parts[1],
            "extra": parts[6] if len(parts) > 6 else "",
        },
        "balance_info": parts[2] or None,
        "price": parts[3],
        "balance_range": parts[4] if len(parts) > 4 else None,
        "account_type": parts[5] if len(parts) > 5 else None,
    }


def _account_type_keyboard() -> InlineKeyboardMarkup:
    account_types = ["CHECKING", "SAVINGS", "BUSINESS", "MONEY MARKET"]
    rows = [[InlineKeyboardButton(text=item, callback_data=f"brute_type:{item}")] for item in account_types]
    rows.append([InlineKeyboardButton(text="❌ Cancel", callback_data="brute_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─── Entry point ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "seller_brute_bank")
async def brute_bank_menu(callback: CallbackQuery, session: AsyncSession, seller, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    if not seller or not seller_actor or not seller_actor.can_upload():
        await callback.answer("❌ Not authorized", show_alert=True)
        return

    if not SellerDepositService.has_upload_access(seller, "brute"):
        await callback.answer(
            "⚠️ Bank package deposit is required to upload Brute Bank items.",
            show_alert=True
        )
        return

    # Показываем список своих brute items
    result = await session.execute(
        select(BruteBankItem)
        .where(BruteBankItem.seller_id == seller.id)
        .order_by(BruteBankItem.created_at.desc())
        .limit(10)
    )
    items = result.scalars().all()

    status_map = {"pending": "⏳", "approved": "✅", "rejected": "❌"}
    lines = ["🔓 *Brute Bank Items*\n"]
    for i in items:
        icon = status_map.get(i.moderation_status, "?")
        lines.append(f"{icon} #{i.id} — {i.bank_name} — ${float(i.buyer_price or i.price):.2f} ({i.status})")

    if not items:
        lines.append("_No items yet. Upload your first one!_")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Upload New Item", callback_data="brute_upload_start")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="seller_menu")],
        ]),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "brute_upload_start")
async def brute_upload_start(callback: CallbackQuery, state: FSMContext, seller, **kwargs):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    await state.clear()
    await state.set_state(BruteUploadStates.waiting_upload_mode)
    await callback.message.edit_text(
        "🔓 *Upload Brute Bank Item*\n\n"
        "Select upload mode:\n\n"
        "Single item = one account.\n"
        "Bulk upload = many accounts in one batch.",
        reply_markup=_upload_mode_keyboard(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("brute_mode:"), BruteUploadStates.waiting_upload_mode)
async def brute_upload_mode(callback: CallbackQuery, state: FSMContext):
    try:
        mode = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Invalid callback", show_alert=True)
        return
    await state.update_data(upload_mode=mode)
    await state.set_state(BruteUploadStates.waiting_bank_name)
    await callback.message.edit_text(
        "🔓 *Upload Brute Bank Item*\n\n"
        "Step 1/6 — Choose how to add bank:\n\n"
        "• *Add existing bank* — enter bank name directly\n"
        "• *Request new bank* — submit for admin approval",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏦 Add existing bank", callback_data="brute_bank_add:existing")],
            [InlineKeyboardButton(text="📝 Request new bank", callback_data="brute_bank_add:request")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="brute_cancel")]
        ]),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("brute_bank_add:"), BruteUploadStates.waiting_bank_name)
async def brute_bank_add_mode(callback: CallbackQuery, state: FSMContext):
    try:
        add_mode = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Invalid callback", show_alert=True)
        return
    
    if add_mode == "request":
        await state.set_state(BruteUploadStates.waiting_request_bank_name)
        await callback.message.edit_text(
            "📝 *Request New Brute Bank*\n\n"
            "Enter the *bank name* you want to add:\n\n"
            "Example: `Chase Bank`, `Wells Fargo`, `Chime`\n\n"
            "⚠️ This will be reviewed by admin within 1-6 hours.\n"
            "You cannot upload to this bank until it is approved.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancel", callback_data="brute_cancel")]
            ]),
            parse_mode="Markdown",
        )
    else:
        await callback.message.edit_text(
            "🔓 *Upload Brute Bank Item*\n\n"
            "Step 1/6 — Enter the *bank name*:\n\n"
            "Example: `Chase Bank`, `Wells Fargo`, `Chime`",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancel", callback_data="brute_cancel")]
            ]),
            parse_mode="Markdown",
        )
    await callback.answer()


# ─── Step 1: Bank name ────────────────────────────────────────────────────────

@router.message(BruteUploadStates.waiting_request_bank_name)
async def brute_request_bank_name_received(message: Message, state: FSMContext):
    bank_name = message.text.strip()
    if len(bank_name) < 2:
        await message.answer("⚠️ Bank name too short. Try again:")
        return
    await state.update_data(request_bank_name=bank_name)
    await state.set_state(BruteUploadStates.waiting_request_bank_code)
    await message.answer(
        "Step 2/5 — Enter the *bank code* (short internal identifier):\n\n"
        "Example: `chase_personal`, `wells_fargo_biz`, `chime_vcc`\n"
        "_Use lowercase letters, numbers, underscores only_\n\n"
        "Send `-` to auto-generate from bank name.",
        parse_mode="Markdown",
    )


@router.message(BruteUploadStates.waiting_request_bank_code)
async def brute_request_bank_code_received(message: Message, state: FSMContext):
    code = message.text.strip()
    data = await state.get_data()
    
    if code == "-":
        # Auto-generate from bank name
        code = data["request_bank_name"].lower().replace(" ", "_").replace("-", "_")
        code = "".join(c for c in code if c.isalnum() or c == "_")
    else:
        code = code.lower().replace(" ", "_")
        if not code.replace("_", "").isalnum():
            await message.answer("⚠️ Use only letters, numbers and underscores. Try again:")
            return
    
    await state.update_data(request_bank_code=code)
    await state.set_state(BruteUploadStates.waiting_request_attributes)
    await message.answer(
        "Step 3/5 — Enter *group attributes* (shown in catalog) or send `-` to skip:\n\n"
        "Example: `AN:RN+INST YODLEE`, `AN:RN+INST FINICITY`",
        parse_mode="Markdown",
    )


@router.message(BruteUploadStates.waiting_request_attributes)
async def brute_request_attributes_received(message: Message, state: FSMContext):
    raw = message.text.strip()
    attributes = None if raw in ("-", "") else raw
    await state.update_data(request_attributes=attributes)
    await state.set_state(BruteUploadStates.waiting_request_category)
    
    await message.answer(
        "Step 4/5 — Select *category*:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 VCC", callback_data="brute_request_cat:vcc")],
            [InlineKeyboardButton(text="👤 Personal", callback_data="brute_request_cat:personal")],
            [InlineKeyboardButton(text="🏢 Business", callback_data="brute_request_cat:business")],
            [InlineKeyboardButton(text="₿ Crypto", callback_data="brute_request_cat:crypto")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="brute_cancel")],
        ]),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("brute_request_cat:"), BruteUploadStates.waiting_request_category)
async def brute_request_category_selected(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller):
    category = callback.data.split(":", 1)[1]
    data = await state.get_data()
    
    # Save the request to database
    from shared.database.models import BruteBankTypeRequest
    
    request = BruteBankTypeRequest(
        seller_id=seller.id,
        requested_name=data["request_bank_name"],
        bank_code=data["request_bank_code"],
        attributes=data.get("request_attributes"),
        category=category,
        status="pending",
    )
    
    session.add(request)
    await session.commit()
    await session.refresh(request)
    
    await state.clear()
    
    cat_labels = {"vcc": "VCC", "personal": "Personal", "business": "Business", "crypto": "Crypto"}
    
    await callback.message.edit_text(
        f"✅ *Brute Bank request submitted!*\n\n"
        f"🏦 Bank: *{data['request_bank_name']}*\n"
        f"🔑 Code: `{data['request_bank_code']}`\n"
        f"🧩 Attributes: {data.get('request_attributes') or '—'}\n"
        f"📂 Category: *{cat_labels.get(category, category)}*\n\n"
        f"📋 Request ID: #{request.id}\n\n"
        f"⏳ Our team will review your request within 1-6 hours.\n"
        f"You will be notified when the bank is approved.\n"
        f"You cannot upload to this bank until it is created.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔓 My Brute Items", callback_data="seller_brute_bank")],
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="seller_menu")],
        ]),
        parse_mode="Markdown",
    )
    await callback.answer()


# ─── Step 1: Bank name (existing flow) ────────────────────────────────────────

@router.message(BruteUploadStates.waiting_bank_name)
async def brute_bank_name_received(message: Message, state: FSMContext):
    bank_name = message.text.strip()
    if len(bank_name) < 2:
        await message.answer("⚠️ Bank name too short. Try again:")
        return
    await state.update_data(bank_name=bank_name)
    await state.set_state(BruteUploadStates.waiting_bank_code)
    await message.answer(
        "Step 2/6 — Enter the *bank code* (short internal identifier):\n\n"
        "Example: `chase_personal`, `wells_fargo_biz`, `chime_vcc`\n"
        "_Use lowercase letters, numbers, underscores only_",
        parse_mode="Markdown",
    )


# ─── Step 2: Bank code ────────────────────────────────────────────────────────

@router.message(BruteUploadStates.waiting_bank_code)
async def brute_bank_code_received(message: Message, state: FSMContext):
    code = message.text.strip().lower().replace(" ", "_")
    if not code.replace("_", "").isalnum():
        await message.answer("⚠️ Use only letters, numbers and underscores. Try again:")
        return
    await state.update_data(bank_code=code)
    await state.set_state(BruteUploadStates.waiting_attributes)
    await message.answer(
        "Step 3/8 — Enter *group attributes* (shown in catalog) or send `-` to skip:\n\n"
        "Example: `AN:RN+INST YODLEE`",
        parse_mode="Markdown",
    )


@router.message(BruteUploadStates.waiting_attributes)
async def brute_attributes_received(message: Message, state: FSMContext):
    raw = message.text.strip()
    attributes = None if raw in ("-", "") else raw
    await state.update_data(attributes=attributes)
    data = await state.get_data()
    if data.get("upload_mode") == "bulk":
        await state.set_state(BruteUploadStates.waiting_bulk_price)
        await message.answer(
            "Step 4/8 — Enter default price for this bulk batch:\n\n"
            "This price will be applied to every parsed row.",
            parse_mode="Markdown",
        )
    else:
        await state.set_state(BruteUploadStates.waiting_balance_range)
        await message.answer(
            "Step 4/8 — Enter *balance range*:\n\n"
            "Examples: `9-12k`, `12-15k`, `21-25k`, `25-35k`",
            parse_mode="Markdown",
        )


@router.message(BruteUploadStates.waiting_balance_range)
async def brute_balance_range_received(message: Message, state: FSMContext):
    balance_range = message.text.strip()
    if len(balance_range) < 2:
        await message.answer("⚠️ Balance range is too short. Example: `9-12k`")
        return
    await state.update_data(balance_range=balance_range)
    await state.set_state(BruteUploadStates.waiting_account_type)
    await message.answer(
        "Step 5/8 — Select *account type*:",
        reply_markup=_account_type_keyboard(),
        parse_mode="Markdown",
    )


@router.message(BruteUploadStates.waiting_bulk_price)
async def brute_bulk_price_received(message: Message, state: FSMContext):
    try:
        price = Decimal(message.text.strip().replace("$", "").replace(",", "."))
        if price <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("⚠️ Invalid price. Enter a positive number like `25` or `49.99`:")
        return
    await state.update_data(default_price=str(price))
    await state.set_state(BruteUploadStates.waiting_bulk_items)
    await message.answer(
        "Step 5/8 — Send one brute item per line:\n\n"
        "<code>BANK|LOGIN|PASS|ACCOUNT_NUMBER|ROUTING|BALANCE|STATE|NAME|ADDRESS</code>\n\n"
        "Example:\n"
        "<code>GTE|john@gmail.com|Qwerty123|123456789|063102152|3200|FL|John Doe|123 Main St, Tampa FL</code>\n"
        "<code>GTE|no|no|123456780|063102152|1800|FL|Jane Doe|77 Pine St, Tampa FL</code>",
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("brute_type:"), BruteUploadStates.waiting_account_type)
async def brute_account_type_selected(callback: CallbackQuery, state: FSMContext):
    account_type = callback.data.split(":", 1)[1]
    await state.update_data(account_type=account_type)
    await state.set_state(BruteUploadStates.waiting_credentials)
    await callback.message.edit_text(
        "Step 6/8 — Enter *credentials*:\n\n"
        "Format (one per line):\n"
        "`login: your_login`\n"
        "`password: your_password`\n"
        "`extra: any additional info`\n\n"
        "You can add as many fields as needed.",
        parse_mode="Markdown",
    )
    await callback.answer()


# ─── Step 4: Credentials ──────────────────────────────────────────────────────

@router.message(BruteUploadStates.waiting_credentials)
async def brute_credentials_received(message: Message, state: FSMContext):
    raw = message.text.strip()
    creds = {}
    for line in raw.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            creds[k.strip()] = v.strip()
        else:
            # Store as raw if no key:value format
            creds["raw"] = raw
            break

    if not creds:
        await message.answer("⚠️ Could not parse credentials. Use `key: value` format.")
        return

    await state.update_data(credentials=creds)
    await state.set_state(BruteUploadStates.waiting_balance)
    await message.answer(
        "Step 7/8 — Enter *balance info* (optional):\n\n"
        "Example: `$12,450.00` or `Unknown`\n"
        "Send `/skip` to skip.",
        parse_mode="Markdown",
    )


# ─── Step 5: Balance ──────────────────────────────────────────────────────────

@router.message(BruteUploadStates.waiting_balance)
async def brute_balance_received(message: Message, state: FSMContext):
    text = message.text.strip()
    balance_info = None if text.lower() in ("/skip", "skip", "-") else text
    await state.update_data(balance_info=balance_info)
    await state.set_state(BruteUploadStates.waiting_price)
    await message.answer(
        "Step 8/8 — Enter your *asking price* (USD):\n\nExample: `25` or `49.99`",
        parse_mode="Markdown",
    )


# ─── Step 6: Price → Confirm ──────────────────────────────────────────────────

@router.message(BruteUploadStates.waiting_price)
async def brute_price_received(message: Message, state: FSMContext):
    try:
        price = Decimal(message.text.strip().replace("$", "").replace(",", "."))
        if price <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("⚠️ Invalid price. Enter a positive number like `25` or `49.99`:")
        return

    await state.update_data(price=str(price))
    data = await state.get_data()
    await state.set_state(BruteUploadStates.confirmation)

    creds_preview = "\n".join(f"  `{k}: {v}`" for k, v in data.get("credentials", {}).items())
    attrs_line = f"🧩 *Group attributes:* {data.get('attributes') or '—'}\n"
    await message.answer(
        f"📋 *Review your Brute Bank item:*\n\n"
        f"🏦 *Bank:* {data['bank_name']}\n"
        f"🔑 *Code:* {data['bank_code']}\n"
        f"{attrs_line}"
        f"📊 *Range:* {data['balance_range']}\n"
        f"🏷 *Type:* {data['account_type']}\n"
        f"💵 *Balance:* {data.get('balance_info') or '—'}\n"
        f"💰 *Price:* ${price:.2f}\n\n"
        f"🔐 *Credentials:*\n{creds_preview}\n\n"
        f"⚠️ Item will be reviewed by admin before becoming available.",
        reply_markup=_confirm_keyboard(),
        parse_mode="Markdown",
    )


# ─── Submit ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "brute_submit", BruteUploadStates.confirmation)
async def brute_submit(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, **kwargs):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return

    data = await state.get_data()
    try:
        if data.get("upload_mode") == "bulk" and data.get("bulk_payload"):
            payload = data["bulk_payload"]
        else:
            payload = {
                "bank_name": data["bank_name"],
                "bank_code": data["bank_code"],
                "upload_mode": "single",
                "balance_range": data["balance_range"],
                "account_type": data["account_type"],
                "balance_info": data.get("balance_info"),
                "price": data["price"],
                "credentials": data["credentials"],
                "attributes": data.get("attributes"),
            }
        batch, created_items, _summary = await SellerUploadPipelineService.create_brute_batch(
            session,
            seller_id=seller.id,
            payload=payload,
        )
        await state.clear()
        first_item = created_items[0]
        gkey = make_brute_group_key(payload["bank_code"], payload.get("attributes"))
        group = await session.scalar(select(BruteBankGroup).where(BruteBankGroup.group_key == gkey))

        if payload["upload_mode"] == "single":
            await _notify_admins_new_brute(first_item)
        else:
            await _notify_admins_new_brute_batch(batch.id, payload["bank_name"], len(created_items))

        await callback.message.edit_text(
            f"✅ *Upload submitted for review!*\n\n"
            f"🏦 {first_item.bank_name} — ${first_item.price:.2f}\n\n"
            f"🛒 Final price: ${float(first_item.buyer_price or first_item.price):.2f}\n"
            f"📦 Batch: #{batch.id} ({batch.upload_mode})\n"
            f"🔢 Items: {len(created_items)}\n"
            f"{'Group matched automatically.' if group else 'Waiting for admin group setup.'}\n"
            f"You will be notified when it's approved or rejected.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔓 My Brute Items", callback_data="seller_brute_bank")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="seller_menu")],
            ]),
        )
    except Exception as e:
        logger.error(f"Failed to save brute bank item: {e}")
        NocoDBService.log_seller_upload(
            seller_id=seller.id,
            category="brute",
            status="failed",
            error_reason=str(e),
            extra={
                "item_type": "brute",
                "bank_name": data.get("bank_name"),
                "bank_code": data.get("bank_code"),
                "upload_mode": data.get("upload_mode"),
            },
        )
        await callback.answer("Error saving item. Please try again.", show_alert=True)
        await state.clear()

    await callback.answer()


@router.message(BruteUploadStates.waiting_bulk_items)
async def brute_bulk_items_received(message: Message, state: FSMContext, session: AsyncSession, seller, **kwargs):
    if not message.text:
        await message.answer("⚠️ Send text lines or upload a .txt/.csv file.")
        return
    data = await state.get_data()
    try:
        normalized, summary = await SellerUploadPipelineService.validate_brute_payload({
            "bank_name": data["bank_name"],
            "bank_code": data["bank_code"],
            "upload_mode": "bulk",
            "bulk_text": message.text,
            "default_price": data.get("default_price"),
            "attributes": data.get("attributes"),
        })
    except ValueError as exc:
        await message.answer(f"⚠️ {exc}")
        return
    await state.update_data(bulk_payload=normalized, bulk_summary=summary)
    await state.set_state(BruteUploadStates.confirmation)
    errors = summary.get("errors", [])[:5]
    errors_text = (
        "Errors: " + "; ".join(f"line {err['line']} {err['error']}" for err in errors)
        if errors else
        "No parsing errors found."
    )
    await message.answer(
        f"📋 *Bulk brute preview*\n\n"
        f"🏦 {normalized['bank_name']}\n"
        f"🔑 {normalized['bank_code']}\n"
        f"✅ Valid items: {summary['valid_items']}\n"
        f"❌ Invalid items: {summary['invalid_items']}\n"
        f"{errors_text}\n\n"
        f"Confirm to submit only the valid rows.",
        parse_mode="Markdown",
        reply_markup=_confirm_keyboard(),
    )


@router.message(BruteUploadStates.waiting_bulk_items, F.document)
async def brute_bulk_file_received(message: Message, state: FSMContext, seller, **kwargs):
    if not message.document:
        return
    filename = (message.document.file_name or "").lower()
    if not filename.endswith((".txt", ".csv")):
        await message.answer("⚠️ Upload a .txt or .csv file.")
        return
    # MIME type whitelist validation
    allowed_mimes = {"text/plain", "text/csv", "application/csv", "application/octet-stream"}
    mime = (message.document.mime_type or "").lower()
    if mime and mime not in allowed_mimes:
        await message.answer("⚠️ Invalid file type. Only plain text (.txt) or CSV (.csv) files are accepted.")
        return
    file = await message.bot.get_file(message.document.file_id)
    downloaded = await message.bot.download_file(file.file_path)
    raw_text = downloaded.read().decode("utf-8", errors="ignore")
    cloned = type("BulkTextMessage", (), {"text": raw_text, "answer": message.answer})()
    await brute_bulk_items_received(cloned, state, None, seller, **kwargs)


@router.callback_query(F.data == "brute_restart")
async def brute_restart(callback: CallbackQuery, state: FSMContext, seller, **kwargs):
    await state.clear()
    await callback.message.edit_text(
        "Upload cancelled. Start over:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Upload New Item", callback_data="brute_upload_start")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="seller_brute_bank")],
        ]),
    )
    await callback.answer()


@router.callback_query(F.data == "brute_cancel")
async def brute_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Upload cancelled.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back", callback_data="seller_brute_bank")]
        ]),
    )
    await callback.answer()


async def _notify_admins_new_brute(item: BruteBankItem):
    """Уведомить администраторов о новом Brute Bank item."""
    try:
        import os
        support_token = os.getenv("SUPPORT_BOT_TOKEN", "")
        admin_ids = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
        if not support_token or not admin_ids:
            return

        from aiogram import Bot
        from aiogram.enums import ParseMode
        bot = Bot(token=support_token)
        text = (
            f"🔓 <b>New Brute Bank Item</b>\n\n"
            f"ID: #{item.id}\n"
            f"Bank: {item.bank_name}\n"
            f"Code: {item.bank_code}\n"
            f"Price: ${item.price:.2f}\n\n"
            f"Review in admin panel: /brute-bank"
        )
        try:
            for admin_id in admin_ids:
                try:
                    await bot.send_message(admin_id, text, parse_mode=ParseMode.HTML)
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_id}: {e}")
        finally:
            await bot.session.close()
    except Exception as e:
        logger.error(f"Failed to notify admins about new brute item: {e}")


async def _notify_admins_new_brute_batch(batch_id: int, bank_name: str, total_items: int):
    """Уведомить администраторов о новой массовой Brute Bank загрузке."""
    try:
        import os
        support_token = os.getenv("SUPPORT_BOT_TOKEN", "")
        admin_ids = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
        if not support_token or not admin_ids:
            return

        from aiogram import Bot
        from aiogram.enums import ParseMode
        bot = Bot(token=support_token)
        text = (
            f"🔓 <b>New Brute Bank Bulk Batch</b>\n\n"
            f"Batch: #{batch_id}\n"
            f"Bank: {bank_name}\n"
            f"Items: {total_items}\n\n"
            f"Review in admin panel: /brute-bank"
        )
        try:
            for admin_id in admin_ids:
                try:
                    await bot.send_message(admin_id, text, parse_mode=ParseMode.HTML)
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_id}: {e}")
        finally:
            await bot.session.close()
    except Exception as e:
        logger.error(f"Failed to notify admins about brute batch: {e}")
