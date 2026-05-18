from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from seller_bot.services.cc_stock_service import CCStockService
from seller_bot.services.special_stock_service import SpecialStockService
from shared.cc_catalog import get_cc_categories
from shared.database.models import SellerEnrollItem, SellerLogsItem, SellerUploadTemplate
from shared.services.seller_deposit_service import SellerDepositService
from shared.services.seller_upload_batch_service import SellerUploadBatchService
from shared.services.seller_upload_pipeline_service import SellerUploadPipelineService
from shared.services.bin_lookup_service import BinLookupService
from sqlalchemy import select

from shared.utils.seller_card_renderers import (
    render_bank_description,
    render_cc_description,
    render_check_description,
    render_nfc_description,
)

router = Router(name="seller_upload_fsm")


UPLOAD_CATEGORIES = {
    "enroll": {
        "label": "🏦 Enroll",
        "format": "zip",
        "parser": "parse_enroll_zip",
        "model": SellerEnrollItem,
    },
    "logs": {
        "label": "📋 Logs",
        "format": "zip",
        "parser": "parse_logs_zip",
        "model": SellerLogsItem,
    },
}


class UploadFSM(StatesGroup):
    waiting_template = State()
    waiting_category = State()
    waiting_type = State()
    waiting_data = State()
    waiting_price = State()
    waiting_preview = State()


def _template_keyboard(templates: list) -> InlineKeyboardMarkup:
    rows = []
    for t in templates[:12]:
        rows.append([InlineKeyboardButton(
            text=f"📋 {t.title} ({t.item_type})",
            callback_data=f"seller_upload_template:{t.id}",
        )])
    rows.append([InlineKeyboardButton(text="➕ Upload New (no template)", callback_data="seller_upload_no_template")])
    rows.append([InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")],
    ])


def _preview_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Submit for Moderation", callback_data="seller_upload_submit")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")],
    ])


def _menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back to Menu", callback_data="seller_menu")],
    ])


def _type_keyboard(family: str) -> InlineKeyboardMarkup:
    if family == "cc":
        rows = [
            [InlineKeyboardButton(text="💳 CC", callback_data="seller_upload_type:cc")],
            [InlineKeyboardButton(text="💳 Debit", callback_data="seller_upload_type:debit")],
        ]
    elif family == "bank":
        rows = [
            [InlineKeyboardButton(text="📋 Logs", callback_data="seller_upload_type:logs")],
            [InlineKeyboardButton(text="🔓 Brute", callback_data="seller_upload_type:brute")],
        ]
    else:
        rows = [
            [InlineKeyboardButton(text="📱 NFC", callback_data="seller_upload_type:nfc")],
            [InlineKeyboardButton(text="🖊 Checks", callback_data="seller_upload_type:check")],
        ]
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="seller_upload_product")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _category_keyboard(session: AsyncSession) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🏦 Bank: Personal", callback_data="seller_upload_category:bank:personal")],
        [InlineKeyboardButton(text="🏢 Bank: Business", callback_data="seller_upload_category:bank:business")],
        [InlineKeyboardButton(text="💳 Bank: VCC", callback_data="seller_upload_category:bank:vcc")],
        [InlineKeyboardButton(text="💸 Bank: Crypto", callback_data="seller_upload_category:bank:crypto")],
    ]
    for category in await get_cc_categories(session):
        rows.append([
            InlineKeyboardButton(
                text=f"💳 CC: {category['name']}",
                callback_data=f"seller_upload_category:cc:{category['code']}",
            )
        ])
    rows.append([InlineKeyboardButton(text="📦 Special Products", callback_data="seller_upload_category:special:special")])
    rows.append([InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _package_code_for_type(type_key: str) -> str:
    if type_key in {"cc", "debit"}:
        return "cc"
    if type_key == "brute":
        return "brute"
    return "bank"


def _data_prompt(type_key: str) -> str:
    prompts = {
        "cc": (
            "Step 3/6 - upload CC data.\n\n"
            "Paste lines or send a .txt file.\n"
            "Flexible format:\n"
            "<code>NUMBER|EXP_MM|EXP_YYYY|CVV|FNAME|LNAME|ADDRESS|CITY|STATE|ZIP|COUNTRY</code>\n"
            "Also supported: <code>NUMBER|MM/YY|CVV|...</code>"
        ),
        "debit": (
            "Step 3/6 - upload Debit data.\n\n"
            "Paste lines or send a .txt file.\n"
            "Format:\n"
            "<code>NUMBER|EXP_MM|EXP_YYYY|CVV|FNAME|LNAME|ADDRESS|CITY|STATE|ZIP|COUNTRY</code>"
        ),
        "logs": (
            "Step 3/6 - upload Logs data.\n\n"
            "Paste lines or send a .txt file.\n"
            "Format:\n"
            "<code>SITE|LOGIN|PASS|COOKIES|BALANCE|STATE|ROUTING|NAME|...</code>"
        ),
        "brute": (
            "Step 3/6 - upload Brute data.\n\n"
            "Paste lines or send a .txt file.\n"
            "Format:\n"
            "<code>BANK|LOGIN|PASS|ACCOUNT_NUMBER|ROUTING|BALANCE|STATE|NAME|ADDRESS</code>"
        ),
        "nfc": (
            "Step 3/6 - upload NFC ZIP.\n\n"
            "Send a ZIP archive containing an <code>.apk</code> file and <code>instruction.txt</code>.\n"
            "Optional metadata inside <code>instruction.txt</code>:\n"
            "<code>bank_name: Chase\ncountry: US\nstate: FL\nzip: 33101\nnfc_type: ap</code>"
        ),
        "check": (
            "Step 3/6 - upload Checks ZIP.\n\n"
            "Send a ZIP archive containing <code>check_data.json</code> and <code>scan.jpg</code>.\n"
            "Required JSON fields: <code>check_type</code>, <code>amount</code>, <code>has_holder_name</code>."
        ),
    }
    return prompts[type_key]


async def _read_document_text(message: Message) -> str:
    file = await message.bot.get_file(message.document.file_id)
    downloaded = await message.bot.download_file(file.file_path)
    return downloaded.read().decode("utf-8", errors="ignore")


async def _read_document_bytes(message: Message) -> bytes:
    file = await message.bot.get_file(message.document.file_id)
    downloaded = await message.bot.download_file(file.file_path)
    return downloaded.read()


def _build_cc_item_name(type_key: str, parsed_lines: list[dict]) -> str:
    brands = {row.get("card_brand") for row in parsed_lines if row.get("card_brand")}
    if len(brands) == 1:
        base = next(iter(brands))
    elif brands:
        base = "Mixed"
    else:
        base = "Uploaded"
    suffix = "Debit" if type_key == "debit" else "CC"
    return f"{base} {suffix}"


def _build_bank_preview(type_key: str, parsed_rows: list[dict]) -> tuple[str, dict, str]:
    sample = parsed_rows[0]
    if type_key == "logs":
        bank_name = sample["site"]
        details = {
            "format": "logs",
            "rows_count": len(parsed_rows),
            "sample": sample,
            "presence": {
                "has_login": bool(sample.get("login")),
                "has_password": bool(sample.get("password")),
                "has_cookies": bool(sample.get("cookies")),
                "has_routing": bool(sample.get("routing_number")),
                "has_holder_name": bool(sample.get("holder_name")),
            },
        }
        preview = render_bank_description(SimpleNamespace(
            bank_name=bank_name,
            state=sample.get("state"),
            stock_count=len(parsed_rows),
            details=details,
        ))
        return bank_name, details, preview

    bank_name = sample["bank_name"]
    details = {
        "format": "bank",
        "rows_count": len(parsed_rows),
        "sample": sample,
        "presence": {
            "has_login": bool(sample.get("login")),
            "has_password": bool(sample.get("password")),
            "has_routing": bool(sample.get("routing_number")),
            "has_holder_name": bool(sample.get("holder_name")),
            "has_account_number": bool(sample.get("account_number")),
            "has_holder_address": bool(sample.get("holder_address")),
        },
    }
    preview = render_bank_description(SimpleNamespace(
        bank_name=bank_name,
        state=sample.get("state"),
        zip=sample.get("zip"),
        stock_count=len(parsed_rows),
        details=details,
    ))
    return bank_name, details, preview


def _preview_text(data: dict) -> str:
    category_label = data.get("category_label", "-")
    type_label = data.get("type_label", "-")
    preview_lines = data.get("summary_lines", [])
    return (
        "Step 5/6 - preview\n\n"
        f"Category: {category_label}\n"
        f"Type: {type_label}\n"
        f"Base price: ${Decimal(str(data['seller_price'])):.2f}\n\n"
        f"{chr(10).join(preview_lines)}\n\n"
        "Step 6/6 - submit to moderation."
    )


@router.callback_query(F.data == "seller_upload_product")
async def seller_upload_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    if not seller or not seller_actor or not seller_actor.can_upload():
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    await state.clear()

    result = await session.execute(
        select(SellerUploadTemplate)
        .where(SellerUploadTemplate.seller_id == seller.id)
        .order_by(SellerUploadTemplate.updated_at.desc())
        .limit(12)
    )
    templates = list(result.scalars().all())

    if templates:
        await state.set_state(UploadFSM.waiting_template)
        await callback.message.edit_text(
            "⬆️ <b>Universal Upload</b>\n\n"
            "Select a saved template to pre-fill your listing details, or start fresh.",
            reply_markup=_template_keyboard(templates),
        )
    else:
        await state.set_state(UploadFSM.waiting_category)
        await callback.message.edit_text(
            "Universal Upload\n\nStep 1/6 - choose category.",
            reply_markup=await _category_keyboard(session),
        )
    await callback.answer()


@router.callback_query(F.data == "seller_upload_no_template", UploadFSM.waiting_template)
async def seller_upload_skip_template(callback: CallbackQuery, state: FSMContext, session: AsyncSession, **kwargs):
    await state.set_state(UploadFSM.waiting_category)
    await callback.message.edit_text(
        "Universal Upload\n\nStep 1/6 - choose category.",
        reply_markup=await _category_keyboard(session),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_upload_template:"), UploadFSM.waiting_template)
async def seller_upload_apply_template(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, **kwargs
):
    template_id = int(callback.data.split(":")[1])
    result = await session.execute(
        select(SellerUploadTemplate).where(
            SellerUploadTemplate.id == template_id,
            SellerUploadTemplate.seller_id == seller.id,
        )
    )
    tpl = result.scalar_one_or_none()
    if not tpl:
        await callback.answer("❌ Template not found", show_alert=True)
        return

    payload = dict(tpl.payload or {})
    type_key = tpl.item_type

    family_map = {
        "cc": "cc", "debit": "cc",
        "logs": "bank", "brute": "bank",
        "nfc": "other", "check": "other",
    }
    family = family_map.get(type_key, "bank")
    await state.update_data(
        upload_family=family,
        upload_type=type_key,
        from_template=True,
        template_id=template_id,
        template_payload=payload,
        **{k: v for k, v in payload.items() if k in (
            "seller_price", "bank_name", "item_name", "has_chat", "has_number_access"
        )},
    )
    await state.set_state(UploadFSM.waiting_data)
    pre_info = ""
    if payload.get("seller_price"):
        pre_info += f"\n💰 Pre-filled price: <b>${payload['seller_price']}</b>"
    if payload.get("bank_name") or payload.get("item_name"):
        pre_info += f"\n🏷 Name: <b>{payload.get('bank_name') or payload.get('item_name','')}</b>"
    await callback.message.edit_text(
        f"📋 <b>Template: {tpl.title}</b>{pre_info}\n\n" + _data_prompt(type_key),
        reply_markup=_cancel_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_upload_category:"), UploadFSM.waiting_category)
async def seller_upload_choose_category(callback: CallbackQuery, state: FSMContext):
    _, family, category_code = callback.data.split(":", 2)
    if family == "cc":
        category_label = f"CC / {category_code}"
    elif family == "bank":
        category_label = f"Bank / {category_code}"
    else:
        category_label = "Special products"
    await state.update_data(upload_family=family, upload_category=category_code, category_label=category_label)
    await state.set_state(UploadFSM.waiting_type)
    await callback.message.edit_text(
        "Step 2/6 - choose product type.",
        reply_markup=_type_keyboard(family),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_upload_type:"), UploadFSM.waiting_type)
async def seller_upload_choose_type(callback: CallbackQuery, state: FSMContext, seller, **kwargs):
    type_key = callback.data.split(":", 1)[1]
    package_code = _package_code_for_type(type_key)
    if not SellerDepositService.has_upload_access(seller, package_code):
        await callback.answer(f"❌ {package_code.upper()} package deposit is required before upload.", show_alert=True)
        return
        type_labels = {
        "cc": "CC",
        "debit": "Debit",
        "logs": "Logs",
        "brute": "Brute",
        "nfc": "NFC",
        "check": "Checks",
    }
    await state.update_data(upload_type=type_key, type_label=type_labels[type_key])
    await state.set_state(UploadFSM.waiting_data)
    await callback.message.edit_text(_data_prompt(type_key), reply_markup=_cancel_keyboard())
    await callback.answer()


@router.message(UploadFSM.waiting_data, F.text | F.document)
async def seller_upload_collect_data(message: Message, state: FSMContext):
    data = await state.get_data()
    type_key = data["upload_type"]
    try:
        if type_key in {"cc", "debit"}:
            raw_text = await _read_document_text(message) if message.document else (message.text or "")
            parsed_lines = []
            for line in [line.strip() for line in raw_text.splitlines() if line.strip()]:
                subtype = "standard" if type_key in {"cc", "debit"} else "with_fullz"
                parsed = SellerUploadPipelineService.parse_cc_line_flexible(line, subtype)
                if not parsed:
                    raise ValueError("CC data contains an invalid line")
                await BinLookupService.enrich_parsed(parsed)
                parsed_lines.append(parsed)
            if not parsed_lines:
                raise ValueError("No valid CC lines found")
            item_name = _build_cc_item_name(type_key, parsed_lines)
            preview = render_cc_description(SimpleNamespace(**parsed_lines[0], item_name=item_name))
            await state.update_data(
                parsed_lines=parsed_lines,
                item_name=item_name,
                summary_lines=[
                    f"Items parsed: {len(parsed_lines)}",
                    f"Title: {item_name}",
                    preview,
                ],
            )
        elif type_key == "logs":
            raw_text = await _read_document_text(message) if message.document else (message.text or "")
            parsed_rows, errors = SellerUploadPipelineService.parse_logs_bulk_text(raw_text)
            if not parsed_rows:
                raise ValueError("No valid log rows found")
            bank_name, details, preview = _build_bank_preview(type_key, parsed_rows)
            await state.update_data(
                parsed_rows=parsed_rows,
                bank_name=bank_name,
                bank_details=details,
                summary_lines=[
                    f"Rows parsed: {len(parsed_rows)}",
                    f"Invalid rows: {len(errors)}",
                    preview,
                ],
            )
        elif type_key == "brute":
            raw_text = await _read_document_text(message) if message.document else (message.text or "")
            preview_rows = [line.strip() for line in raw_text.splitlines() if line.strip()]
            if not preview_rows:
                raise ValueError("No brute rows found")
            first_parts = [part.strip() for part in preview_rows[0].split("|")]
            bank_name = first_parts[0] if first_parts and first_parts[0] else "Brute Upload"
            await state.update_data(
                brute_text=raw_text,
                bank_name=bank_name,
                summary_lines=[
                    f"Rows detected: {len(preview_rows)}",
                    f"Bank: {bank_name}",
                    "Price will be applied to every valid brute row in this batch.",
                ],
            )
        elif type_key == "nfc":
            if not message.document:
                raise ValueError("Send a ZIP archive for NFC upload")
            archive_info = SellerUploadPipelineService.inspect_nfc_archive(await _read_document_bytes(message))
            preview = render_nfc_description(SimpleNamespace(
                bank_name=archive_info["bank_name"],
                nfc_type=archive_info["nfc_type"],
                country=archive_info["country"],
                state=archive_info.get("state"),
                zip=archive_info.get("zip"),
                data_file_path=message.document.file_id,
            ))
            await state.update_data(
                archive_info=archive_info,
                file_id=message.document.file_id,
                summary_lines=archive_info["preview_lines"] + [preview],
            )
        else:
            if not message.document:
                raise ValueError("Send a ZIP archive for Checks upload")
            archive_info = SellerUploadPipelineService.inspect_check_archive(await _read_document_bytes(message))
            preview = render_check_description(SimpleNamespace(
                bank_name=archive_info["bank_name"],
                check_type=archive_info["check_type"],
                amount=Decimal(archive_info["amount"]),
                state=archive_info.get("state"),
                zip=archive_info.get("zip"),
                has_holder_name=archive_info["has_holder_name"],
                has_address=archive_info["has_address"],
                scan_file_path=message.document.file_id,
                template_file_path=None,
            ))
            await state.update_data(
                archive_info=archive_info,
                file_id=message.document.file_id,
                summary_lines=archive_info["preview_lines"] + [preview],
            )
    except ValueError as exc:
        await message.answer(str(exc))
        return

    await state.set_state(UploadFSM.waiting_price)
    await message.answer("Step 4/6 - enter base price in USD.")


@router.message(UploadFSM.waiting_price, F.text)
async def seller_upload_collect_price(message: Message, state: FSMContext):
    try:
        price = SellerUploadPipelineService.parse_price(message.text)
    except ValueError as exc:
        await message.answer(str(exc))
        return
    await state.update_data(seller_price=str(price))
    data = await state.get_data()
    await state.set_state(UploadFSM.waiting_preview)
    await message.answer(_preview_text(data), reply_markup=_preview_keyboard())


@router.callback_query(F.data == "seller_upload_submit", UploadFSM.waiting_preview)
async def seller_upload_submit(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller):
    data = await state.get_data()
    type_key = data["upload_type"]
    price = Decimal(str(data["seller_price"]))

    if type_key in {"cc", "debit"}:
        parsed_lines = data["parsed_lines"]
        item_name = data["item_name"]
        batch = await SellerUploadBatchService.create_batch(
            session,
            seller_id=seller.id,
            item_type="cc",
            upload_mode="bulk" if len(parsed_lines) > 1 else "single",
            title=item_name,
            total_items=len(parsed_lines),
            draft_payload={"upload_type": type_key, "category_code": data["upload_category"]},
            validation_summary={"preview_lines": data["summary_lines"]},
            submitted=True,
        )
        for idx, parsed in enumerate(parsed_lines, start=1):
            suffix = (parsed.get("number") or str(idx))[-6:]
            cc_code = f"s{seller.id}_{type_key}_{suffix}_{idx}"[:100]
            await CCStockService.add_cc_item(
                session,
                seller_id=seller.id,
                item_name=item_name,
                category_code=data["upload_category"],
                cc_code=cc_code,
                seller_price=price,
                description=render_cc_description(SimpleNamespace(**parsed, item_name=item_name)),
                instruction="Uploaded via universal upload",
                product_subtype="standard",
                extra_data=parsed.get("extra_data"),
                parsed_data=parsed,
                upload_batch_id=batch.id,
            )
        success_text = f"CC batch submitted for moderation.\nBatch #{batch.id}\nItems: {len(parsed_lines)}"
    elif type_key == "brute":
        payload, summary = SellerUploadPipelineService.parse_brute_universal_text(data["brute_text"], price)
        batch, created_items, _ = await SellerUploadPipelineService.create_brute_batch(
            session,
            seller_id=seller.id,
            payload=payload,
        )
        success_text = f"Brute batch submitted for moderation.\nBatch #{batch.id}\nItems: {len(created_items)}\n{chr(10).join(summary['preview_lines'])}"
    elif type_key == "logs":
        parsed_rows = data["parsed_rows"]
        bank_name = data["bank_name"]
        bank_details = data["bank_details"]
        sample = parsed_rows[0]
        payload = {
            "bank_name": bank_name,
            "category": data["upload_category"],
            "product_type": "bank",
            "product_subtype": "log",
            "seller_price": str(price),
            "stock_count": len(parsed_rows),
            "state": sample.get("state"),
            "zip": sample.get("zip"),
            "has_name": bool(sample.get("holder_name")),
            "description": render_bank_description(SimpleNamespace(
                bank_name=bank_name,
                state=sample.get("state"),
                zip=sample.get("zip"),
                stock_count=len(parsed_rows),
                details=bank_details,
            )),
            "instruction": "Uploaded via universal upload",
            "details": bank_details,
        }
        batch, bank, _ = await SellerUploadPipelineService.create_bank_batch(
            session,
            seller_id=seller.id,
            markup_percent=0,
            payload=payload,
        )
        success_text = f"{data['type_label']} batch submitted for moderation.\nBatch #{batch.id}\nQty: {bank.stock_count}"
    elif type_key == "nfc":
        archive_info = data["archive_info"]
        batch = await SellerUploadBatchService.create_batch(
            session,
            seller_id=seller.id,
            item_type="nfc",
            upload_mode="single",
            title=archive_info["bank_name"],
            total_items=1,
            draft_payload=archive_info,
            validation_summary={"preview_lines": data["summary_lines"]},
            submitted=True,
        )
        item = await SpecialStockService.add_nfc_item(
            session,
            seller_id=seller.id,
            upload_batch_id=batch.id,
            item_name=f"{'Apple Pay' if archive_info['nfc_type'] == 'ap' else 'Google Pay'} | {archive_info['bank_name']}",
            nfc_type=archive_info["nfc_type"],
            product_subtype="apple_pay" if archive_info["nfc_type"] == "ap" else "google_pay",
            bank_name=archive_info["bank_name"],
            country=archive_info["country"],
            state=archive_info.get("state"),
            zip=archive_info.get("zip"),
            seller_price=price,
            base_price=price,
            buyer_price=price,
            data_file_path=data["file_id"],
            description=render_nfc_description(SimpleNamespace(
                bank_name=archive_info["bank_name"],
                nfc_type=archive_info["nfc_type"],
                country=archive_info["country"],
                state=archive_info.get("state"),
                zip=archive_info.get("zip"),
                data_file_path=data["file_id"],
            )),
            instruction=f"Archive: {archive_info['apk_name']}",
            moderation_status="pending_moderation",
            is_in_stock=True,
            is_active=True,
        )
        success_text = f"NFC item submitted for moderation.\nBatch #{batch.id}\nItem: {item.item_name}"
    else:
        archive_info = data["archive_info"]
        batch = await SellerUploadBatchService.create_batch(
            session,
            seller_id=seller.id,
            item_type="check",
            upload_mode="single",
            title=archive_info["bank_name"],
            total_items=1,
            draft_payload=archive_info,
            validation_summary={"preview_lines": data["summary_lines"]},
            submitted=True,
        )
        item = await SpecialStockService.add_check_item(
            session,
            seller_id=seller.id,
            upload_batch_id=batch.id,
            item_name=f"{archive_info['bank_name']} {archive_info['check_type'].title()} Check | ${Decimal(archive_info['amount']):.0f} | {archive_info.get('state') or '-'}",
            check_type=archive_info["check_type"],
            bank_name=archive_info["bank_name"],
            amount=Decimal(archive_info["amount"]),
            state=archive_info.get("state"),
            zip=archive_info.get("zip"),
            has_holder_name=archive_info["has_holder_name"],
            has_address=archive_info["has_address"],
            check_date=date.fromisoformat(archive_info["check_date"]) if archive_info.get("check_date") else None,
            seller_description=archive_info.get("seller_description"),
            scan_file_path=data["file_id"],
            seller_price=price,
            base_price=price,
            buyer_price=price,
            moderation_status="pending_moderation",
            is_in_stock=True,
            is_active=True,
        )
        success_text = f"Check item submitted for moderation.\nBatch #{batch.id}\nItem: {item.item_name}"

    # Auto-save as template (upsert by type+name for convenience)
    try:
        tpl_payload: dict = {
            "upload_type": type_key,
            "seller_price": str(price),
        }
        for k in ("bank_name", "item_name", "has_chat", "has_number_access", "upload_category"):
            if data.get(k) is not None:
                tpl_payload[k] = data[k]
        tpl_title = (
            data.get("bank_name") or data.get("item_name") or data.get("type_label") or type_key
        )[:200]
        existing_tpl = await session.execute(
            select(SellerUploadTemplate).where(
                SellerUploadTemplate.seller_id == seller.id,
                SellerUploadTemplate.item_type == type_key,
                SellerUploadTemplate.title == tpl_title,
            )
        )
        existing_tpl = existing_tpl.scalar_one_or_none()
        if existing_tpl:
            existing_tpl.payload = tpl_payload
        else:
            session.add(SellerUploadTemplate(
                seller_id=seller.id,
                item_type=type_key,
                title=tpl_title,
                payload=tpl_payload,
            ))
        await session.commit()
    except Exception:
        pass

    await state.clear()
    await callback.message.edit_text(success_text, reply_markup=_menu_keyboard())
    await callback.answer("Submitted", show_alert=True)
