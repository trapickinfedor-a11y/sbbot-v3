"""Seller bot: My Listings overview + bulk repricing for all product types."""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import SellerBank, SellerCCItem

logger = logging.getLogger(__name__)
router = Router(name="seller_listings")

PAGE_SIZE = 15


class RepriceFSM(StatesGroup):
    waiting_price = State()
    waiting_bulk_price = State()


def _listings_kb(banks: list, cc_items: list, page: int, total: int) -> InlineKeyboardMarkup:
    rows = []
    for b in banks[:PAGE_SIZE]:
        stock = "✅" if b.is_in_stock else "❌"
        rows.append([InlineKeyboardButton(
            text=f"{stock} {b.bank_name[:22]} | ${b.seller_price}",
            callback_data=f"sl_bank:{b.id}",
        )])
    for c in cc_items[:PAGE_SIZE - len(banks)]:
        status = "✅" if c.moderation_status == "approved" else "⏳"
        rows.append([InlineKeyboardButton(
            text=f"{status} {c.item_name[:22]} | ${c.seller_price}",
            callback_data=f"sl_cc:{c.id}",
        )])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀ Prev", callback_data=f"sl_page:{page-1}"))
    if (page + 1) * PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(text="Next ▶", callback_data=f"sl_page:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="💰 Bulk Reprice All", callback_data="sl_bulk_reprice")])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data="seller_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _item_detail_kb(item_type: str, item_id: int, is_in_stock: bool = True) -> InlineKeyboardMarkup:
    toggle_text = "❌ Set Out of Stock" if is_in_stock else "✅ Set In Stock"
    rows = [
        [InlineKeyboardButton(text="💰 Change Price", callback_data=f"sl_reprice:{item_type}:{item_id}")],
    ]
    if item_type == "bank":
        rows.append([InlineKeyboardButton(text=toggle_text, callback_data=f"sl_toggle:{item_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Back to Listings", callback_data="seller_my_listings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _load_page(session: AsyncSession, seller_id: int, page: int):
    offset = page * PAGE_SIZE
    banks_res = await session.execute(
        select(SellerBank)
        .where(and_(SellerBank.seller_id == seller_id, SellerBank.is_active == True))
        .order_by(SellerBank.id.desc())
        .limit(PAGE_SIZE)
        .offset(offset)
    )
    banks = list(banks_res.scalars().all())

    cc_res = await session.execute(
        select(SellerCCItem)
        .where(SellerCCItem.seller_id == seller_id)
        .order_by(SellerCCItem.id.desc())
        .limit(max(0, PAGE_SIZE - len(banks)))
        .offset(max(0, offset - PAGE_SIZE))
    )
    cc_items = list(cc_res.scalars().all())

    total_banks = await session.scalar(
        select(func.count(SellerBank.id))
        .where(and_(SellerBank.seller_id == seller_id, SellerBank.is_active == True))
    ) or 0
    total_cc = await session.scalar(
        select(func.count(SellerCCItem.id))
        .where(SellerCCItem.seller_id == seller_id)
    ) or 0

    return banks, cc_items, int(total_banks) + int(total_cc)


@router.callback_query(F.data == "seller_my_listings")
@router.callback_query(F.data.startswith("sl_page:"))
async def listings_view(callback: CallbackQuery, state: FSMContext, session: AsyncSession, seller, **kwargs):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    page = 0
    if callback.data.startswith("sl_page:"):
        page = int(callback.data.split(":")[1])

    banks, cc_items, total = await _load_page(session, seller.id, page)

    in_stock = sum(1 for b in banks if b.is_in_stock)
    approved_cc = sum(1 for c in cc_items if c.moderation_status == "approved")

    await callback.message.edit_text(
        f"📋 <b>My Listings</b>\n\n"
        f"🏦 Banks: {len(banks)} (✅ {in_stock} in stock)\n"
        f"💳 CC Items: {len(cc_items)} (✅ {approved_cc} approved)\n"
        f"📊 Total: {total}\n\n"
        f"Tap an item to change price or toggle stock.",
        reply_markup=_listings_kb(banks, cc_items, page, total),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sl_bank:"))
async def listings_bank_detail(callback: CallbackQuery, session: AsyncSession, seller, **kwargs):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    bank_id = int(callback.data.split(":")[1])
    bank = await session.get(SellerBank, bank_id)
    if not bank or bank.seller_id != seller.id:
        await callback.answer("❌ Not found", show_alert=True)
        return
    await callback.message.edit_text(
        f"🏦 <b>{bank.bank_name}</b>\n\n"
        f"💰 Price: <b>${bank.seller_price}</b>\n"
        f"📦 Qty: {bank.stock_count}\n"
        f"Stock: {'✅ In stock' if bank.is_in_stock else '❌ Out of stock'}",
        reply_markup=_item_detail_kb("bank", bank_id, bank.is_in_stock),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sl_cc:"))
async def listings_cc_detail(callback: CallbackQuery, session: AsyncSession, seller, **kwargs):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    cc_id = int(callback.data.split(":")[1])
    cc = await session.get(SellerCCItem, cc_id)
    if not cc or cc.seller_id != seller.id:
        await callback.answer("❌ Not found", show_alert=True)
        return
    await callback.message.edit_text(
        f"💳 <b>{cc.item_name}</b>\n\n"
        f"💰 Price: <b>${cc.seller_price}</b>\n"
        f"Status: {cc.moderation_status}",
        reply_markup=_item_detail_kb("cc", cc_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("sl_toggle:"))
async def listings_toggle_stock(callback: CallbackQuery, session: AsyncSession, seller, **kwargs):
    if not seller:
        await callback.answer("❌ Not authorized", show_alert=True)
        return
    bank_id = int(callback.data.split(":")[1])
    bank = await session.get(SellerBank, bank_id)
    if not bank or bank.seller_id != seller.id:
        await callback.answer("❌ Not found", show_alert=True)
        return
    bank.is_in_stock = not bank.is_in_stock
    await session.commit()
    await callback.answer("✅ In Stock" if bank.is_in_stock else "❌ Out of Stock")
    await callback.message.edit_text(
        f"🏦 <b>{bank.bank_name}</b>\n\n"
        f"💰 Price: <b>${bank.seller_price}</b>\n"
        f"📦 Qty: {bank.stock_count}\n"
        f"Stock: {'✅ In stock' if bank.is_in_stock else '❌ Out of stock'}",
        reply_markup=_item_detail_kb("bank", bank_id, bank.is_in_stock),
    )


@router.callback_query(F.data.startswith("sl_reprice:"))
async def listings_reprice_start(callback: CallbackQuery, state: FSMContext, **kwargs):
    _, item_type, item_id = callback.data.split(":")
    await state.set_state(RepriceFSM.waiting_price)
    await state.update_data(reprice_type=item_type, reprice_id=int(item_id))
    await callback.message.edit_text(
        f"💰 Enter new price in USD for this item (e.g. <code>49.99</code>):\n\n"
        f"Send /cancel to go back.",
    )
    await callback.answer()


@router.message(RepriceFSM.waiting_price, F.text)
async def listings_reprice_set(message: Message, state: FSMContext, session: AsyncSession, seller, **kwargs):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back to Listings", callback_data="seller_my_listings")]
        ]))
        return
    try:
        new_price = Decimal(message.text.strip().replace(",", "."))
        if new_price <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("❌ Invalid price. Enter a positive number, e.g. <code>49.99</code>.")
        return

    data = await state.get_data()
    item_type = data["reprice_type"]
    item_id = data["reprice_id"]
    await state.clear()

    if item_type == "bank":
        item = await session.get(SellerBank, item_id)
        if item and item.seller_id == seller.id:
            item.seller_price = new_price
            await session.commit()
            await message.answer(f"✅ Price updated to <b>${new_price}</b>.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Back to Listings", callback_data="seller_my_listings")]
            ]))
        else:
            await message.answer("❌ Item not found.")
    elif item_type == "cc":
        item = await session.get(SellerCCItem, item_id)
        if item and item.seller_id == seller.id:
            item.seller_price = new_price
            await session.commit()
            await message.answer(f"✅ Price updated to <b>${new_price}</b>.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Back to Listings", callback_data="seller_my_listings")]
            ]))
        else:
            await message.answer("❌ Item not found.")


@router.callback_query(F.data == "sl_bulk_reprice")
async def listings_bulk_reprice_start(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.set_state(RepriceFSM.waiting_bulk_price)
    await callback.message.edit_text(
        "💰 <b>Bulk Reprice</b>\n\n"
        "Enter new price — it will be applied to <b>all your in-stock banks AND approved CC items</b>.\n\n"
        "e.g. <code>49.99</code>\n\n"
        "Send /cancel to abort.",
    )
    await callback.answer()


@router.message(RepriceFSM.waiting_bulk_price, F.text)
async def listings_bulk_reprice_set(message: Message, state: FSMContext, session: AsyncSession, seller, **kwargs):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back to Listings", callback_data="seller_my_listings")]
        ]))
        return
    try:
        new_price = Decimal(message.text.strip().replace(",", "."))
        if new_price <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("❌ Invalid price. Enter a positive number.")
        return

    await state.clear()

    bank_res = await session.execute(
        select(SellerBank).where(and_(SellerBank.seller_id == seller.id, SellerBank.is_active == True))
    )
    banks = list(bank_res.scalars().all())
    bank_count = 0
    for b in banks:
        b.seller_price = new_price
        bank_count += 1

    cc_res = await session.execute(
        select(SellerCCItem).where(
            and_(SellerCCItem.seller_id == seller.id, SellerCCItem.moderation_status == "approved")
        )
    )
    cc_items = list(cc_res.scalars().all())
    cc_count = 0
    for c in cc_items:
        c.seller_price = new_price
        cc_count += 1

    await session.commit()
    await message.answer(
        f"✅ <b>Bulk reprice complete!</b>\n\n"
        f"🏦 Banks updated: {bank_count}\n"
        f"💳 CC items updated: {cc_count}\n"
        f"💰 New price: <b>${new_price}</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Back to Listings", callback_data="seller_my_listings")]
        ]),
    )
