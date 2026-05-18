from __future__ import annotations

"""
CC (Credit Cards) seller panel - Add to existing / Create new type
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal, InvalidOperation
from typing import Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from seller_bot.keyboards.inline import (
    cc_category_keyboard, cc_type_keyboard, seller_cc_list, cc_non_vbv_keyboard
)
from seller_bot.services.cc_stock_service import CCStockService
from shared.cc_catalog import get_cc_categories, get_cc_types_for_category, get_cc_item_name
from shared.services.seller_deposit_service import SellerDepositService
from shared.services.seller_upload_batch_service import SellerUploadBatchService
from shared.utils.seller_product_meta import cc_item_badge
from shared.services.seller_upload_pipeline_service import SellerUploadPipelineService
from shared.services.nocodb_service import NocoDBService
from shared.services.bin_lookup_service import BinLookupService

logger = logging.getLogger(__name__)
router = Router(name="seller_cc_stock")


class AddCCStates(StatesGroup):
    waiting_category = State()
    waiting_non_vbv = State()
    waiting_add_mode = State()
    waiting_cc_type = State()
    waiting_name = State()
    waiting_price = State()
    waiting_description = State()
    waiting_instruction = State()
    waiting_upload_mode = State()
    waiting_extra_data = State()
    waiting_bulk_lines = State()


def _cc_upload_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣ Single item", callback_data="seller_cc_upload:single")],
        [InlineKeyboardButton(text="📦 Bulk upload", callback_data="seller_cc_upload:bulk")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")],
    ])


@router.callback_query(F.data == "seller_my_cc")
async def my_cc_handler(callback: CallbackQuery, session: AsyncSession, seller, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    if not seller or not seller_actor or not seller_actor.can_upload():
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    
    items = await CCStockService.get_seller_cc_items(session, seller.id)
    
    if not items:
        await callback.message.edit_text(
            "💳 <b>My CC Items</b>\n\n"
            "You don't have any CC items yet.\n"
            "Press <b>Add CC Item</b> to create your first position.",
            reply_markup=seller_cc_list([])
        )
    else:
        approved = sum(1 for i in items if i.moderation_status == "approved")
        pending = sum(1 for i in items if i.moderation_status == "pending_moderation")
        await callback.message.edit_text(
            f"💳 <b>My CC Items</b> ({len(items)} total)\n\n"
            f"✅ Approved: {approved}\n"
            f"⏳ Pending: {pending}\n\n"
            f"Tap an item to manage:",
            reply_markup=seller_cc_list(items)
        )
    await callback.answer()


@router.callback_query(F.data == "seller_add_cc")
async def add_cc_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, **kwargs):
    seller_actor = kwargs.get("seller_actor")
    if not seller or not seller_actor or not seller_actor.can_upload():
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    if not SellerDepositService.has_upload_access(seller, "cc"):
        await callback.answer(
            "❌ CC package deposit is required before you can upload CC items.",
            show_alert=True
        )
        return

    categories = await get_cc_categories(session)
    await state.set_state(AddCCStates.waiting_category)
    await callback.message.edit_text(
        "➕ <b>Add CC Item</b>\n\nSelect category:",
        reply_markup=cc_category_keyboard(categories)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_cc_cat:"), AddCCStates.waiting_category)
async def add_cc_category_step(callback: CallbackQuery, state: FSMContext, **kwargs):
    try:
        category_code = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Invalid callback", show_alert=True)
        return
    await state.update_data(category_code=category_code)
    await state.set_state(AddCCStates.waiting_non_vbv)
    await callback.message.edit_text(
        "🔓 <b>NON-VBV?</b>\n\n"
        "Mark entire batch as NON-VBV (3-D Secure bypass cards)?",
        reply_markup=cc_non_vbv_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_cc_non_vbv:"), AddCCStates.waiting_non_vbv)
async def add_cc_non_vbv(callback: CallbackQuery, state: FSMContext, session: AsyncSession, **kwargs):
    try:
        is_non_vbv = callback.data.split(":")[1] == "yes"
    except IndexError:
        await callback.answer("Invalid callback", show_alert=True)
        return
    product_subtype = "non_vbv" if is_non_vbv else "cc"
    await state.update_data(is_non_vbv=is_non_vbv, product_subtype=product_subtype)
    await state.set_state(AddCCStates.waiting_add_mode)
    data = await state.get_data()
    category_code = data["category_code"]

    cc_types = await get_cc_types_for_category(session, category_code)
    non_vbv_label = "🔓 NON-VBV" if is_non_vbv else "💳 Regular"
    if cc_types:
        await callback.message.edit_text(
            f"🧩 Product: <b>{non_vbv_label}</b>\n"
            f"📂 Category: <b>{category_code.upper()}</b>\n\n"
            "Choose how to add:\n"
            "• <b>Add to existing type</b> — select from catalog\n"
            "• <b>Create new type</b> — enter your own item name",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Add to existing type", callback_data="seller_cc_mode:existing")],
                [InlineKeyboardButton(text="🆕 Create new type", callback_data="seller_cc_mode:new")],
                [InlineKeyboardButton(text="❌ Cancel", callback_data="seller_menu")]
            ])
        )
    else:
        await state.set_state(AddCCStates.waiting_name)
        await callback.message.edit_text(
            f"🧩 Product: <b>{non_vbv_label}</b>\n"
            "No types in this category. Enter the <b>item name</b>:\n"
            "Example: <i>Visa Classic, MC Gold</i>"
        )
    await callback.answer()




@router.callback_query(F.data.startswith("seller_cc_mode:"), AddCCStates.waiting_add_mode)
async def add_cc_mode(callback: CallbackQuery, state: FSMContext, session: AsyncSession, **kwargs):
    try:
        mode = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Invalid callback", show_alert=True)
        return
    data = await state.get_data()
    category_code = data["category_code"]
    
    if mode == "existing":
        cc_types = await get_cc_types_for_category(session, category_code)
        if not cc_types:
            await callback.answer("No types. Use Create new type.", show_alert=True)
            return
        
        await state.set_state(AddCCStates.waiting_cc_type)
        await callback.message.edit_text(
            "📋 Select the <b>CC type</b> from catalog:",
            reply_markup=cc_type_keyboard(cc_types, category_code)
        )
    else:
        await state.set_state(AddCCStates.waiting_name)
        await callback.message.edit_text(
            "Enter the <b>item name</b> (new type):\n"
            f"Example: <i>Visa Classic, MC Gold</i>"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("seller_cc_type:"), AddCCStates.waiting_cc_type)
async def add_cc_type_selected(callback: CallbackQuery, state: FSMContext, session: AsyncSession, **kwargs):
    parts = callback.data.split(":")
    category_code = parts[1]
    base_cc_code = parts[2]
    
    item_name = await get_cc_item_name(session, base_cc_code)
    data = await state.get_data()
    cc_code = f"cc_{data.get('product_subtype', 'cc')}__{base_cc_code}"[:100]
    
    await state.update_data(cc_code=cc_code, item_name=item_name)
    await state.set_state(AddCCStates.waiting_price)
    data = await state.get_data()
    
    await callback.message.edit_text(
        f"💳 Item: <b>{item_name}</b>\n\n"
        f"🧩 Product: <b>{cc_item_badge(data.get('product_subtype', 'cc'))}</b>\n\n"
        f"Enter your <b>price in USD</b>:\n"
        f"Example: <i>50</i> or <i>120.50</i>\n\n"
        f"This is your base price. Final buyer price is assigned during moderation."
    )
    await callback.answer()


@router.message(AddCCStates.waiting_name, F.text)
async def add_cc_name(message: Message, state: FSMContext, seller, **kwargs):
    item_name = message.text.strip()
    if len(item_name) < 2 or len(item_name) > 100:
        await message.answer("❌ Name must be 2-100 characters. Try again:")
        return
    
    slug = item_name.lower().replace(" ", "_").replace("-", "_")
    data = await state.get_data()
    cc_code = f"s{seller.id}_cc_{data.get('product_subtype', 'cc')}_{slug}"[:100]
    
    await state.update_data(item_name=item_name, cc_code=cc_code)
    await state.set_state(AddCCStates.waiting_price)
    data = await state.get_data()
    
    await message.answer(
        f"💳 Item: <b>{item_name}</b>\n\n"
        f"🧩 Product: <b>{cc_item_badge(data.get('product_subtype', 'cc'))}</b>\n\n"
        f"Enter your <b>price in USD</b>:\n"
        f"Example: <i>50</i> or <i>120.50</i>"
    )


@router.message(AddCCStates.waiting_price, F.text)
async def add_cc_price(message: Message, state: FSMContext, session: AsyncSession, seller, **kwargs):
    try:
        price = Decimal(message.text.strip().replace("$", "").replace(",", "."))
        if price <= 0 or price > 50000:
            await message.answer("❌ Price must be between $0.01 and $50,000. Try again:")
            return
    except (InvalidOperation, ValueError):
        await message.answer("❌ Invalid price. Enter a number:")
        return
    
    data = await state.get_data()
    cc_code = data.get("cc_code", "")
    
    await state.update_data(seller_price=float(price))
    await state.set_state(AddCCStates.waiting_description)
    
    await message.answer(
        f"💰 Your price: <b>${price:.2f}</b>\n"
        f"📊 Final buyer price will be set by moderation.\n\n"
        f"Enter <b>description</b> (optional). Send <b>-</b> to skip."
    )


def _parse_cc_line(
    text: str,
    product_subtype: str,
    item_name: str | None = None,
    is_non_vbv: bool = False,
) -> Optional[dict]:
    return SellerUploadPipelineService.parse_cc_line_flexible(
        text, product_subtype, item_name, is_non_vbv=is_non_vbv
    )


@router.message(AddCCStates.waiting_description, F.text)
async def add_cc_description(message: Message, state: FSMContext, **kwargs):
    description = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(description=description)
    await state.set_state(AddCCStates.waiting_instruction)
    await message.answer(
        "📘 Enter <b>instruction</b> for this CC item (optional).\n\n"
        "Use it for ZIP/fullz notes or delivery instructions.\n"
        "Send <b>-</b> to skip."
    )


@router.message(AddCCStates.waiting_instruction, F.text)
async def add_cc_instruction(message: Message, state: FSMContext, **kwargs):
    instruction = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(instruction=instruction)
    await state.set_state(AddCCStates.waiting_upload_mode)
    await message.answer(
        "📥 Select upload mode for CC:\n\n"
        "Single item = one card/item.\n"
        "Bulk upload = multiple lines in one batch.",
        reply_markup=_cc_upload_mode_keyboard(),
    )


_CC_FORMAT_HINT = (
    "Format — pipe-separated, fields after CVV are optional:\n"
    "<code>NUMBER|EXP|CVV|TYPE|BRAND|LVL|BANK|COUNTRY|HOLDER|ADDR|STATE|CITY|ZIP|Info|REF|PRICE</code>\n\n"
    "EXP: <code>10/26</code> or <code>10/2026</code>\n\n"
    "Examples:\n"
    "<code>4432644901621883|10/26|194|DEBIT|Visa|CLASSIC|U.S. BANK N.A.|US|Jesse Van Der Sluis|155 Rita Way|NY|Albany|42701||base01|14</code>\n"
    "<code>5500005555555559|11/29|222|CREDIT|Mastercard|GOLD|CHASE|GB|John Smith|10 High St|LND|London|SW1A|||18</code>\n"
    "<code>4111111111111111|06/27|123</code>"
)


@router.callback_query(F.data.startswith("seller_cc_upload:"), AddCCStates.waiting_upload_mode)
async def cc_upload_mode(callback: CallbackQuery, state: FSMContext, **kwargs):
    try:
        mode = callback.data.split(":")[1]
    except IndexError:
        await callback.answer("Invalid callback", show_alert=True)
        return
    data = await state.get_data()
    non_vbv_badge = " 🔓 NON-VBV" if data.get("is_non_vbv") else ""
    if mode == "single":
        await state.set_state(AddCCStates.waiting_extra_data)
        await callback.message.edit_text(
            f"📋 <b>Card details</b>{non_vbv_badge}\n\n" + _CC_FORMAT_HINT
        )
    else:
        await state.set_state(AddCCStates.waiting_bulk_lines)
        await callback.message.edit_text(
            f"📦 <b>Bulk CC upload</b>{non_vbv_badge}\n\n"
            "One card per line.\n\n" + _CC_FORMAT_HINT
        )
    await callback.answer()


@router.message(AddCCStates.waiting_extra_data, F.text)
async def add_cc_extra_data(message: Message, state: FSMContext, session: AsyncSession, seller, **kwargs):
    data = await state.get_data()
    product_subtype = data.get("product_subtype", "cc")
    is_non_vbv = bool(data.get("is_non_vbv", False))
    parsed = _parse_cc_line(message.text.strip(), product_subtype, data.get("item_name"), is_non_vbv=is_non_vbv)
    if not parsed:
        NocoDBService.log_seller_upload(
            seller_id=seller.id,
            category=data.get("category_code"),
            status="failed",
            error_reason="Invalid CC line",
            extra={
                "item_type": "cc",
                "item_name": data.get("item_name"),
                "product_subtype": product_subtype,
            },
        )
        await message.answer(
            "❌ Invalid CC line.\n\n" + _CC_FORMAT_HINT,
            parse_mode="HTML",
        )
        return
    await BinLookupService.enrich_parsed(parsed)
    await state.clear()
    
    cc_code = data.get("cc_code")
    item_name = data.get("item_name")
    category_code = data["category_code"]
    
    if not cc_code:
        cc_code = f"s{seller.id}_{item_name.lower().replace(' ', '_')}"
    
    description = data.get("description")
    batch = await SellerUploadBatchService.create_batch(
        session,
        seller_id=seller.id,
        item_type="cc",
        upload_mode="single",
        title=item_name,
        total_items=1,
    )
    
    line_price = parsed.get("seller_price") or Decimal(str(data["seller_price"]))
    item = await CCStockService.add_cc_item(
        session,
        seller_id=seller.id,
        item_name=item_name,
        category_code=category_code,
        cc_code=cc_code,
        seller_price=line_price,
        description=description,
        instruction=data.get("instruction"),
        product_subtype=data.get("product_subtype", "cc"),
        extra_data=parsed.get("extra_data"),
        parsed_data=parsed,
        upload_batch_id=batch.id,
    )
    
    await message.answer(
        f"✅ <b>CC Item added!</b>\n\n"
        f"💳 {item.item_name}\n"
        f"🧩 Product: {cc_item_badge(getattr(item, 'product_subtype', 'cc'))}\n"
        f"📂 Category: {item.category_code}\n"
        f"💰 Your price: ${item.seller_price:.2f}\n"
        f"🛒 Final price: ${item.buyer_price:.2f}\n"
        f"📦 Batch: #{batch.id} (single)\n"
        f"📊 Status: ⏳ Pending moderation",
        reply_markup=seller_cc_list(await CCStockService.get_seller_cc_items(session, seller.id))
    )


@router.message(AddCCStates.waiting_bulk_lines, F.text)
async def add_cc_bulk_lines(message: Message, state: FSMContext, session: AsyncSession, seller, **kwargs):
    raw_lines = [line.strip() for line in message.text.splitlines() if line.strip()]
    data = await state.get_data()
    product_subtype = data.get("product_subtype", "cc")
    is_non_vbv = bool(data.get("is_non_vbv", False))
    parsed_lines = []
    for line in raw_lines:
        parsed = _parse_cc_line(line, product_subtype, data.get("item_name"), is_non_vbv=is_non_vbv)
        if not parsed:
            NocoDBService.log_seller_upload(
                seller_id=seller.id,
                category=data.get("category_code"),
                status="failed",
                error_reason=f"Invalid CC bulk line: {line}",
                extra={
                    "item_type": "cc",
                    "item_name": data.get("item_name"),
                    "product_subtype": product_subtype,
                },
            )
            await message.answer(
                f"❌ Invalid line:\n<code>{line}</code>\n\n" + _CC_FORMAT_HINT,
                parse_mode="HTML",
            )
            return
        await BinLookupService.enrich_parsed(parsed)
        parsed_lines.append(parsed)
    if not parsed_lines:
        NocoDBService.log_seller_upload(
            seller_id=seller.id,
            category=data.get("category_code"),
            status="failed",
            error_reason="No valid CC lines found",
            extra={"item_type": "cc", "item_name": data.get("item_name"), "product_subtype": product_subtype},
        )
        await message.answer("❌ No valid lines found.")
        return
    if len(parsed_lines) > 200:
        await message.answer("❌ Maximum 200 lines per bulk upload.")
        return

    await state.clear()

    batch = await SellerUploadBatchService.create_batch(
        session,
        seller_id=seller.id,
        item_type="cc",
        upload_mode="bulk",
        title=data.get("item_name"),
        total_items=len(parsed_lines),
    )

    batch_price = Decimal(str(data["seller_price"]))
    created = 0
    for idx, parsed in enumerate(parsed_lines, start=1):
        suffix = (parsed.get("number") or str(idx))[-6:]
        cc_code = f"{data.get('cc_code')}_{idx}_{suffix}"[:100]
        # Per-line PRICE column overrides the batch price when present
        line_price = parsed.get("seller_price") or batch_price
        await CCStockService.add_cc_item(
            session,
            seller_id=seller.id,
            item_name=data["item_name"],
            category_code=data["category_code"],
            cc_code=cc_code,
            seller_price=line_price,
            description=data.get("description"),
            instruction=data.get("instruction"),
            product_subtype=data.get("product_subtype", "cc"),
            extra_data=parsed.get("extra_data"),
            parsed_data=parsed,
            upload_batch_id=batch.id,
        )
        created += 1

    await message.answer(
        f"✅ <b>Bulk CC batch uploaded!</b>\n\n"
        f"💳 Item: {data['item_name']}\n"
        f"🧩 Product: {cc_item_badge(data.get('product_subtype', 'cc'))}\n"
        f"📦 Batch: #{batch.id} (bulk)\n"
        f"🔢 Items created: {created}\n"
        f"💰 Base price: ${batch_price:.2f} (per-line PRICE overrides if set)\n"
        f"📊 Status: ⏳ Pending moderation",
        reply_markup=seller_cc_list(await CCStockService.get_seller_cc_items(session, seller.id)),
    )


@router.callback_query(F.data.startswith("seller_cc_item:"))
async def cc_item_detail(callback: CallbackQuery, session: AsyncSession, seller, **kwargs):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    
    item_id = int(callback.data.split(":")[1])
    item = await CCStockService.get_cc_item_by_id(session, item_id)
    
    if not item or item.seller_id != seller.id:
        await callback.answer("❌ Item not found", show_alert=True)
        return
    
    status_map = {"approved": "✅ Approved", "pending_moderation": "⏳ Pending", "rejected": "❌ Rejected"}
    status = status_map.get(item.moderation_status, item.moderation_status)
    
    text = (
        f"💳 <b>{item.item_name}</b>\n\n"
        f"🧩 Product: {cc_item_badge(getattr(item, 'product_subtype', 'cc'))}\n"
        f"📂 Category: {item.category_code}\n"
        f"💰 Your price: ${item.seller_price:.2f}\n"
        f"🛒 Final price: ${item.buyer_price:.2f}\n"
        f"📊 Status: {status}"
    )
    if item.description:
        text += f"\n📝 {item.description}"
    if getattr(item, "instruction", None):
        text += f"\n📘 {item.instruction}"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back to My CC", callback_data="seller_my_cc")]
    ])
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()
