from __future__ import annotations

"""
Mirror Bot - Brute Bank handler:
bank list -> search/pagination -> variants -> concrete purchase.
"""

import logging
from datetime import datetime, timedelt, timezone
from decimal import Decimal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from mirror_bot.services.order_service import OrderService
from mirror_bot.services.checkout_coupon_service import CheckoutCouponService
from mirror_bot.services.user_service import UserService
from mirror_bot.states.banks import BankStates
from mirror_bot.states.order import OrderStates
from mirror_bot.utils.message_utils import safe_edit_message
from shared.database.models import BruteBankGroup, BruteBankItem, BruteBankOrder, Seller
from shared.services.seller_conversation_service import get_or_create_conversation
from shared.services.ledger_service import LedgerService
from shared.services.guarantee_policy_service import is_guarantee_active
from shared.services.nocodb_service import NocoDBService

logger = logging.getLogger(__name__)
router = Router()

BRUTE_GROUPS_PER_PAGE = 12


BRUTE_CHECK_WINDOW = 60   # 60 minutes — fixed for Brute BA (no direct chat, screenshot refund)


def _brute_result_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ Report Issue (Screenshot)", callback_data=f"brute_report:{order_id}")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")],
    ])


def _brute_refund_options_keyboard(order_id: int, conv_id: int) -> InlineKeyboardMarkup:
    """Refund options for Brute BA: ask seller first OR moderation."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Ask Seller First", callback_data=f"buyer_chat_conv:{conv_id}:{order_id}")],
        [InlineKeyboardButton(text="📋 Request Moderation", callback_data=f"brute_moderation:{order_id}")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")],
    ])


def _escape_markdown(value: str) -> str:
    escaped = value
    for ch in ("\\", "_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"):
        escaped = escaped.replace(ch, f"\\{ch}")
    return escaped


async def _fetch_brute_groups(session: AsyncSession, search_query: str | None, page: int, *, alpha_sort: str = "az") -> tuple[list[dict], int, int, int]:
    inventory_subquery = (
        select(
            BruteBankItem.group_id.label("group_id"),
            func.count(BruteBankItem.id).label("available_count"),
        )
        .where(
            BruteBankItem.group_id.is_not(None),
            BruteBankItem.moderation_status == "approved",
            BruteBankItem.status == "available",
            BruteBankItem.is_active == True,
        )
        .group_by(BruteBankItem.group_id)
        .subquery()
    )

    stmt = (
        select(BruteBankGroup, inventory_subquery.c.available_count)
        .join(inventory_subquery, inventory_subquery.c.group_id == BruteBankGroup.id)
        .where(BruteBankGroup.is_active == True)
    )
    if search_query:
        term = f"%{search_query.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(BruteBankGroup.bank_name).like(term),
                func.lower(BruteBankGroup.bank_code).like(term),
                func.lower(func.coalesce(BruteBankGroup.attributes, "")).like(term),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total_groups = int((await session.execute(count_stmt)).scalar() or 0)
    total_pages = max(1, (total_groups + BRUTE_GROUPS_PER_PAGE - 1) // BRUTE_GROUPS_PER_PAGE)
    current_page = max(0, min(page, total_pages - 1))

    name_order = BruteBankGroup.bank_name.desc() if alpha_sort == "za" else BruteBankGroup.bank_name.asc()
    rows = (
        await session.execute(
            stmt.order_by(name_order)
            .offset(current_page * BRUTE_GROUPS_PER_PAGE)
            .limit(BRUTE_GROUPS_PER_PAGE)
        )
    ).all()

    groups = [
        {
            "id": group.id,
            "bank_name": group.bank_name,
            "bank_code": group.bank_code,
            "attributes": group.attributes,
            "available_count": int(available_count or 0),
        }
        for group, available_count in rows
    ]
    return groups, total_groups, current_page, total_pages


def _brute_search_prompt_keyboard(buttons) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=buttons.CANCEL, callback_data="brute_search_cancel")],
    ])


def _brute_groups_keyboard(groups: list[dict], page: int, total_pages: int, buttons, *, search_query: str | None = None, alpha_sort: str = "az") -> InlineKeyboardMarkup:
    mode = "search" if search_query else "all"
    rows: list[list[InlineKeyboardButton]] = []

    search_row = [InlineKeyboardButton(text=buttons.SEARCH, callback_data="brute_search")]
    if search_query:
        search_row.append(InlineKeyboardButton(text="✖️ Clear", callback_data="brute_clear_search"))
    alpha_next = "za" if alpha_sort == "az" else "az"
    alpha_label = "A→Z" if alpha_sort == "az" else "Z→A"
    search_row.append(InlineKeyboardButton(text=alpha_label, callback_data=f"brute_alpha:{alpha_next}:{mode}"))
    rows.append(search_row)

    for group in groups:
        attrs = f" [{group['attributes']}]" if group.get("attributes") else ""
        rows.append([
            InlineKeyboardButton(
                text=f"{group['bank_name']}{attrs} [{group['available_count']}]",
                callback_data=f"brute_group:{group['id']}:{page}:{mode}:asc",
            )
        ])

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text=buttons.PREV, callback_data=f"brute_page:{page - 1}:{mode}:{alpha_sort}"))
    nav_row.append(InlineKeyboardButton(text=buttons.PAGE_INFO.format(page=page + 1, total_pages=total_pages), callback_data="brute_noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text=buttons.NEXT, callback_data=f"brute_page:{page + 1}:{mode}:{alpha_sort}"))
    rows.append(nav_row)

    rows.append([InlineKeyboardButton(text=buttons.BACK, callback_data="banks_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _build_brute_groups_view(session: AsyncSession, buttons, *, page: int = 0, search_query: str | None = None, alpha_sort: str = "az"):
    groups, total_groups, current_page, total_pages = await _fetch_brute_groups(session, search_query, page, alpha_sort=alpha_sort)

    if search_query:
        safe_query = _escape_markdown(search_query)
        text = (
            "🔓 *Brute BANK*\n\n"
            f"🔎 Search: {safe_query}\n"
            f"🏦 Found banks: {total_groups}\n\n"
        )
        if groups:
            text += "Select bank:"
        else:
            text += "No banks matched your search. Try another keyword."
    else:
        text = (
            "🔓 *Brute BANK*\n\n"
            f"🏦 Available banks: {total_groups}\n\n"
        )
        if groups:
            text += "Select bank:"
        else:
            text += "No brute banks are available right now."

    keyboard = _brute_groups_keyboard(groups, current_page, total_pages, buttons, search_query=search_query, alpha_sort=alpha_sort)
    return text, keyboard


async def _render_brute_groups(callback: CallbackQuery, session: AsyncSession, state: FSMContext, buttons, *, page: int = 0, search_query: str | None = None, alpha_sort: str = "az"):
    text, keyboard = await _build_brute_groups_view(session, buttons, page=page, search_query=search_query, alpha_sort=alpha_sort)

    await safe_edit_message(
        callback,
        text,
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


async def _render_brute_groups_message(message: Message, session: AsyncSession, buttons, *, page: int = 0, search_query: str | None = None, alpha_sort: str = "az"):
    text, keyboard = await _build_brute_groups_view(session, buttons, page=page, search_query=search_query, alpha_sort=alpha_sort)
    await message.answer(
        text,
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "banks_brute")
async def brute_bank_main(callback: CallbackQuery, state: FSMContext, session: AsyncSession, buttons):
    await state.clear()
    await state.update_data(brute_search_query=None)
    await _render_brute_groups(callback, session, state, buttons, page=0, search_query=None)
    await callback.answer()


@router.callback_query(F.data == "brute_search")
async def brute_search_prompt(callback: CallbackQuery, state: FSMContext, buttons):
    current_data = await state.get_data()
    current_query = current_data.get("brute_search_query")
    prompt = (
        "🔎 *Search Brute Bank*\n\n"
        "Send bank name, bank code, or keyword.\n"
        "Examples: `chase`, `wells`, `otp`"
    )
    if current_query:
        prompt += f"\n\nCurrent search: {_escape_markdown(current_query)}"

    await state.set_state(BankStates.waiting_brute_search_query)
    await state.update_data(brute_search_prompt_message_id=callback.message.message_id)
    await safe_edit_message(
        callback,
        prompt,
        reply_markup=_brute_search_prompt_keyboard(buttons),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "brute_search_cancel")
async def brute_search_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession, buttons):
    data = await state.get_data()
    search_query = data.get("brute_search_query")
    await state.update_data(brute_search_prompt_message_id=None)
    await state.set_state(None)
    await _render_brute_groups(callback, session, state, buttons, page=0, search_query=search_query)
    await callback.answer()


@router.callback_query(F.data == "brute_clear_search")
async def brute_clear_search(callback: CallbackQuery, state: FSMContext, session: AsyncSession, buttons):
    await state.update_data(brute_search_query=None, brute_search_prompt_message_id=None)
    await state.set_state(None)
    await _render_brute_groups(callback, session, state, buttons, page=0, search_query=None)
    await callback.answer()


@router.message(BankStates.waiting_brute_search_query, F.text)
async def brute_search_query_received(message: Message, state: FSMContext, session: AsyncSession, buttons):
    query = (message.text or "").strip()
    data = await state.get_data()
    prompt_message_id = data.get("brute_search_prompt_message_id")
    if query.lower() in {"/cancel", "cancel"}:
        await state.update_data(brute_search_query=None, brute_search_prompt_message_id=None)
        await state.set_state(None)
        if prompt_message_id:
            text, keyboard = await _build_brute_groups_view(session, buttons, page=0, search_query=None)
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=prompt_message_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
            try:
                await message.delete()
            except Exception:
                pass
        else:
            await _render_brute_groups_message(message, session, buttons, page=0, search_query=None)
        return
    if len(query) < 2:
        await message.answer("⚠️ Send at least 2 characters for search.")
        return

    await state.update_data(brute_search_query=query, brute_search_prompt_message_id=None)
    await state.set_state(None)
    if prompt_message_id:
        text, keyboard = await _build_brute_groups_view(session, buttons, page=0, search_query=query)
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=prompt_message_id,
            text=text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
        try:
            await message.delete()
        except Exception:
            pass
    else:
        await _render_brute_groups_message(message, session, buttons, page=0, search_query=query)


@router.callback_query(F.data.startswith("brute_page:"))
async def brute_groups_page(callback: CallbackQuery, state: FSMContext, session: AsyncSession, buttons):
    parts = callback.data.split(":")
    page = int(parts[1])
    mode = parts[2]
    alpha = parts[3] if len(parts) > 3 and parts[3] in ("az", "za") else "az"
    data = await state.get_data()
    search_query = data.get("brute_search_query") if mode == "search" else None
    await _render_brute_groups(callback, session, state, buttons, page=page, search_query=search_query, alpha_sort=alpha)
    await callback.answer()


@router.callback_query(F.data.startswith("brute_alpha:"))
async def brute_alpha_toggle(callback: CallbackQuery, state: FSMContext, session: AsyncSession, buttons):
    parts = callback.data.split(":")
    alpha = parts[1] if len(parts) > 1 and parts[1] in ("az", "za") else "az"
    mode = parts[2] if len(parts) > 2 else "all"
    data = await state.get_data()
    search_query = data.get("brute_search_query") if mode == "search" else None
    await _render_brute_groups(callback, session, state, buttons, page=0, search_query=search_query, alpha_sort=alpha)
    await callback.answer()


@router.callback_query(F.data == "brute_noop")
async def brute_noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("brute_back_list:"))
async def brute_back_to_list(callback: CallbackQuery, state: FSMContext, session: AsyncSession, buttons):
    parts = callback.data.split(":")
    page = int(parts[1])
    mode = parts[2] if len(parts) > 2 else "all"
    alpha = parts[3] if len(parts) > 3 and parts[3] in ("az", "za") else "az"
    data = await state.get_data()
    search_query = data.get("brute_search_query") if mode == "search" else None
    await _render_brute_groups(callback, session, state, buttons, page=page, search_query=search_query, alpha_sort=alpha)
    await callback.answer()


@router.callback_query(F.data.startswith("brute_group:"))
async def brute_group_handler(callback: CallbackQuery, session: AsyncSession):
    parts = callback.data.split(":")
    if len(parts) < 4:
        await callback.answer("❌ Bad request", show_alert=True)
        return
    _, group_id_str, page_str, mode = parts[:4]
    sort = parts[4] if len(parts) > 4 and parts[4] in ("asc", "desc") else "asc"
    group_id = int(group_id_str)
    page = int(page_str)
    group = await session.scalar(
        select(BruteBankGroup).where(
            BruteBankGroup.id == group_id,
            BruteBankGroup.is_active == True,
        )
    )
    if not group:
        await callback.answer("❌ Group not found", show_alert=True)
        return

    price_col = func.coalesce(BruteBankItem.buyer_price, BruteBankItem.price)
    order_price = price_col.desc() if sort == "desc" else price_col.asc()
    variant_stmt = (
        select(
            BruteBankItem.balance_range,
            BruteBankItem.account_type,
            price_col.label("display_price"),
            func.count(BruteBankItem.id).label("quantity"),
        )
        .where(
            BruteBankItem.group_id == group_id,
            BruteBankItem.moderation_status == "approved",
            BruteBankItem.status == "available",
            BruteBankItem.is_active == True,
        )
        .group_by(
            BruteBankItem.balance_range,
            BruteBankItem.account_type,
            price_col,
        )
        .order_by(order_price, BruteBankItem.balance_range, BruteBankItem.account_type)
    )
    variants = (await session.execute(variant_stmt)).all()

    rows = []
    for row in variants:
        quantity = int(row.quantity or 0)
        if quantity <= 0:
            continue
        label = f"{row.balance_range or 'NoRange'} {row.account_type or 'NO TYPE'} | ${float(row.display_price):.2f} [{quantity}]"
        rows.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"brute_variant:{group_id}:{row.balance_range or '-'}:{row.account_type or '-'}:{float(row.display_price):.2f}:{page}:{mode}:{sort}",
            )
        ])

    sort_next = "desc" if sort == "asc" else "asc"
    sort_label = "💰 Low → High" if sort == "asc" else "💰 High → Low"
    rows.append([
        InlineKeyboardButton(
            text=f"{sort_label} (toggle)",
            callback_data=f"brute_group:{group_id}:{page}:{mode}:{sort_next}",
        )
    ])
    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data=f"brute_back_list:{page}:{mode}")])
    subtitle = f"\n\n{group.attributes}" if group.attributes else ""
    await safe_edit_message(
        callback,
        f"🔓 *{group.bank_name}*{subtitle}\n\nSelect variant:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("brute_variant:"))
async def brute_variant_handler(callback: CallbackQuery, session: AsyncSession, mirror_bot_id: int):
    parts = callback.data.split(":", 7)
    if len(parts) < 7:
        await callback.answer("❌ Bad request", show_alert=True)
        return
    _, group_id_str, balance_range, account_type, price_str, page_str, mode = parts[:7]
    sort = parts[7] if len(parts) > 7 and parts[7] in ("asc", "desc") else "asc"
    group_id = int(group_id_str)
    page = int(page_str)
    price = Decimal(price_str)
    group = await session.scalar(select(BruteBankGroup).where(BruteBankGroup.id == group_id))
    if not group:
        await callback.answer("❌ Group not found", show_alert=True)
        return

    quantity_q = await session.execute(
        select(func.count()).where(
            BruteBankItem.group_id == group_id,
            BruteBankItem.balance_range == (None if balance_range == "-" else balance_range),
            BruteBankItem.account_type == (None if account_type == "-" else account_type),
            func.coalesce(BruteBankItem.buyer_price, BruteBankItem.price) == price,
            BruteBankItem.moderation_status == "approved",
            BruteBankItem.status == "available",
            BruteBankItem.is_active == True,
        )
    )
    quantity = int(quantity_q.scalar() or 0)
    user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
    balance = user.balance if user else Decimal("0")

    await safe_edit_message(
        callback,
        (
            f"🔓 *{group.bank_name}*\n\n"
            f"📊 *Range:* {balance_range if balance_range != '-' else '—'}\n"
            f"🏷 *Type:* {account_type if account_type != '-' else '—'}\n"
            f"💰 *Price:* ${price:.2f}\n"
            f"📦 *Available:* {quantity}\n"
            f"💳 *Your balance:* ${balance:.2f}"
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"⚡ Buy Now | ${price:.2f}", callback_data=f"brute_buy:{group_id}:{balance_range}:{account_type}:{price_str}:{page}:{mode}:{sort}")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data=f"brute_group:{group_id}:{page}:{mode}:{sort}")],
        ]),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("brute_buy:"))
async def brute_item_buy(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int):
    parts = callback.data.split(":", 7)
    if len(parts) < 7:
        await callback.answer("❌ Bad request", show_alert=True)
        return
    _, group_id_str, balance_range, account_type, price_str, page_str, mode = parts[:7]
    sort = parts[7] if len(parts) > 7 and parts[7] in ("asc", "desc") else "asc"
    group_id = int(group_id_str)
    price = Decimal(price_str)
    page = int(page_str)

    group = await session.scalar(
        select(BruteBankGroup).where(
            BruteBankGroup.id == group_id,
            BruteBankGroup.is_active == True,
        )
    )
    if not group:
        await callback.answer("❌ Group not found", show_alert=True)
        return

    text = (
        f"⚠️ Confirm purchase?\n\n"
        f"🏦 {group.bank_name}\n"
        f"📊 Range: {balance_range if balance_range != '-' else '—'}\n"
        f"🏷 Type: {account_type if account_type != '-' else '—'}\n"
        f"💵 ${price:.2f} will be deducted.\n"
        f"🛡 Verify window: 60 minutes"
    )
    await state.update_data(
        checkout_category="banks",
        checkout_service_name=f"brute_{group.bank_name.lower()}",
        checkout_base_price=str(price),
        checkout_confirm_text=text,
        checkout_keyboard_type="custom",
        checkout_confirm_callback=f"brute_buy_confirm:{group_id}:{balance_range}:{account_type}:{price_str}:{page}:{mode}:{sort}",
        checkout_cancel_callback=f"brute_variant:{group_id}:{balance_range}:{account_type}:{price_str}:{page}:{mode}:{sort}",
        checkout_parse_mode=None,
        selected_coupon_code=None,
        selected_user_coupon_id=None,
    )
    await state.set_state(OrderStates.confirmation)

    await safe_edit_message(
        callback,
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Confirm", callback_data=f"brute_buy_confirm:{group_id}:{balance_range}:{account_type}:{price_str}:{page}:{mode}:{sort}")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data=f"brute_variant:{group_id}:{balance_range}:{account_type}:{price_str}:{page}:{mode}:{sort}")],
        ]),
        parse_mode=None,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("brute_buy_confirm:"))
async def brute_item_buy_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession, mirror_bot_id: int):
    parts = callback.data.split(":", 7)
    if len(parts) < 7:
        await callback.answer("❌ Bad request", show_alert=True)
        return
    _, group_id_str, balance_range, account_type, price_str, _page_str, _mode = parts[:7]
    group_id = int(group_id_str)
    price = Decimal(price_str)
    balance_range_val = None if balance_range == "-" else balance_range
    account_type_val = None if account_type == "-" else account_type

    group = await session.scalar(
        select(BruteBankGroup).where(
            BruteBankGroup.id == group_id,
            BruteBankGroup.is_active == True,
        )
    )
    if not group:
        await callback.answer("❌ Group not found", show_alert=True)
        return

    item = await session.scalar(
        select(BruteBankItem).where(
            BruteBankItem.group_id == group_id,
            BruteBankItem.balance_range == balance_range_val,
            BruteBankItem.account_type == account_type_val,
            func.coalesce(BruteBankItem.buyer_price, BruteBankItem.price) == price,
            BruteBankItem.moderation_status == "approved",
            BruteBankItem.status == "available",
            BruteBankItem.is_active == True,
        ).order_by(BruteBankItem.id)
    )
    if not item:
        await callback.answer("❌ This variant is no longer available", show_alert=True)
        return

    try:
        state_data = await state.get_data()
        pricing = await CheckoutCouponService.get_checkout_pricing(
            session,
            telegram_user_id=callback.from_user.id,
            state_data={
                "checkout_category": "banks",
                "checkout_service_name": f"brute_{group.bank_name.lower()}",
                "checkout_base_price": str(price),
                "selected_coupon_code": state_data.get("selected_coupon_code"),
            },
        )
        success = await OrderService.charge_balance(
            session,
            callback.from_user.id,
            pricing.final_amount,
            description=f"Brute bank purchase {group.bank_name}",
            commit=False,
        )
        if not success:
            await callback.answer("❌ Balance update failed", show_alert=True)
            return

        sale_result = await session.execute(
            update(BruteBankItem)
            .where(
                BruteBankItem.id == item.id,
                BruteBankItem.status == "available",
            )
            .values(
                status="sold",
                buyer_user_id=callback.from_user.id,
                mirror_bot_id=mirror_bot_id,
                sold_at=datetime.now(timezone.utc),
            )
        )
        if not sale_result.rowcount:
            await session.rollback()
            await callback.answer("❌ This variant is no longer available", show_alert=True)
            return

        seller = await session.scalar(select(Seller).where(Seller.id == item.seller_id))
        if seller:
            seller.total_orders += 1
            await LedgerService.credit_seller_balance(
                session,
                seller_id=seller.id,
                amount=Decimal(str(item.base_price or item.price)),
                description=f"Brute bank sale #{item.id}",
                related_entity_type="brute_bank_item",
                related_entity_id=item.id,
                idempotency_key=LedgerService.build_idempotency_key("brute-bank-sale", item.id),
            )

        now = datetime.now(timezone.utc)

        brute_order = BruteBankOrder(
            brute_bank_item_id=item.id,
            seller_id=item.seller_id,
            buyer_user_id=callback.from_user.id,
            mirror_bot_id=mirror_bot_id,
            status="completed",
            price_for_buyer=pricing.final_amount,
            price_for_seller=item.base_price or item.price,
            check_window_minutes=BRUTE_CHECK_WINDOW,
            delivered_at=now,
            auto_complete_at=now + timedelta(hours=24),
        )
        session.add(brute_order)
        await session.commit()
        await state.clear()
        if pricing.applied:
            NocoDBService.log_event(
                event_type="coupon_applied",
                actor_type="buyer",
                actor_id=callback.from_user.id,
                target_type="brute_bank_order",
                target_id=brute_order.id,
                status="applied",
                payload={
                    "coupon_code": pricing.code,
                    "category": "banks",
                    "service_name": f"brute_{group.bank_name.lower()}",
                    "original_amount": float(pricing.original_amount),
                    "discount_amount": float(pricing.discount_amount),
                    "final_amount": float(pricing.final_amount),
                },
                timestamp=now,
            )

        user = await UserService.get_user(session, callback.from_user.id, mirror_bot_id)
        reveal_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Open Product", callback_data=f"brute_reveal:{brute_order.id}")],
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")],
        ])
        await safe_edit_message(
            callback,
            (
                f"✅ *Purchase #{brute_order.id} successful!*\n\n"
                f"🏦 *Bank:* {group.bank_name}\n"
                f"📊 *Range:* {item.balance_range or '—'}\n"
                f"🏷 *Type:* {item.account_type or '—'}\n"
                f"💰 *Paid:* ${price:.2f}\n"
                f"💳 *Your balance:* ${user.balance:.2f}\n\n"
                f"⚠️ *Press the button below to open your product\\.*\n"
                f"You will have *{BRUTE_CHECK_WINDOW} minutes* to verify\\.\n"
                f"After that, payment is finalized to the seller\\."
            ),
            reply_markup=reveal_kb,
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.error("Brute bank purchase failed: %s", exc)
        await session.rollback()
        await callback.answer("❌ Purchase failed. Please try again.", show_alert=True)
        return

    await callback.answer()


@router.callback_query(F.data.startswith("brute_feedback:"))
async def brute_feedback(callback: CallbackQuery, session: AsyncSession):
    _, order_id, feedback_status = callback.data.split(":")
    order = await session.scalar(select(BruteBankOrder).where(BruteBankOrder.id == int(order_id)))
    if not order or order.buyer_user_id != callback.from_user.id:
        await callback.answer("Order not found", show_alert=True)
        return
    order.feedback_status = feedback_status
    order.feedback_at = datetime.now(timezone.utc)
    seller = await session.scalar(select(Seller).where(Seller.id == order.seller_id))
    if seller:
        if feedback_status == "liked":
            seller.likes_count = int(seller.likes_count or 0) + 1
        else:
            seller.dislikes_count = int(seller.dislikes_count or 0) + 1
    await session.commit()
    await safe_edit_message(
        callback,
        "Feedback saved.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")]]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("brute_report:"))
async def brute_report(callback: CallbackQuery, session: AsyncSession):
    order_id = int(callback.data.split(":")[1])
    order = await session.scalar(select(BruteBankOrder).where(BruteBankOrder.id == order_id))
    if not order or order.buyer_user_id != callback.from_user.id:
        await callback.answer("Order not found", show_alert=True)
        return
    if not is_guarantee_active(order.check_expires_at):
        await callback.answer("Guarantee window expired (60 min)", show_alert=True)
        return
    order.report_status = "reported"
    order.reported_at = datetime.now(timezone.utc)
    conv = await get_or_create_conversation(
        session,
        seller_id=order.seller_id,
        buyer_user_id=order.buyer_user_id,
        mirror_bot_id=order.mirror_bot_id,
        source_order_type="brute",
        source_order_id=order.id,
    )
    await session.commit()
    await safe_edit_message(
        callback,
        (
            "📹 Refund Request\n\n"
            "📸 Screenshot proof is required.\n"
            "We recommend asking the seller directly first — "
            "most issues are resolved quickly that way.\n\n"
            "If the seller doesn't respond, request moderation."
        ),
        reply_markup=_brute_refund_options_keyboard(order.id, conv.id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("brute_moderation:"))
async def brute_moderation(callback: CallbackQuery, session: AsyncSession):
    """Buyer requests moderation for Brute BA order."""
    order_id = int(callback.data.split(":")[1])
    order = await session.scalar(select(BruteBankOrder).where(BruteBankOrder.id == order_id))
    if not order or order.buyer_user_id != callback.from_user.id:
        await callback.answer("Order not found", show_alert=True)
        return
    order.report_status = "moderation_requested"
    await session.commit()
    try:
        from shared.services.admin_notification_service import AdminNotificationService
        await AdminNotificationService.notify_new_dispute(
            order_type="brute_bank",
            order_id=order.id,
            buyer_user_id=callback.from_user.id,
            seller_id=order.seller_id,
        )
    except Exception:
        pass
    await safe_edit_message(
        callback,
        (
            "✅ Moderation request submitted.\n\n"
            "📸 Prepare your screenshot proof.\n"
            "You will receive a notification when a decision is made."
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")],
        ]),
    )
    await callback.answer()


# ============================================
# REVEAL FLOW
# ============================================

@router.callback_query(F.data.startswith("brute_reveal:"))
async def brute_reveal_handler(callback: CallbackQuery, session: AsyncSession):
    """Buyer opens Brute Bank product — starts the guarantee timer and shows credentials."""
    order_id = int(callback.data.split(":")[1])
    order = await session.scalar(select(BruteBankOrder).where(BruteBankOrder.id == order_id))
    if not order or order.buyer_user_id != callback.from_user.id:
        await callback.answer("Order not found", show_alert=True)
        return

    now = datetime.now(timezone.utc)
    if not order.check_started_at:
        order.check_started_at = now
        order.check_expires_at = now + timedelta(minutes=BRUTE_CHECK_WINDOW)
        order.auto_complete_at = order.check_expires_at
        await session.commit()

    item = await session.scalar(select(BruteBankItem).where(BruteBankItem.id == order.brute_bank_item_id))
    creds_lines = ""
    if item and item.credentials:
        creds_lines = "\n".join(f"`{k}: {v}`" for k, v in item.credentials.items())

    group = await session.scalar(select(BruteBankGroup).where(BruteBankGroup.id == item.group_id)) if item else None
    bank_name = group.bank_name if group else "Bank"

    await safe_edit_message(
        callback,
        (
            f"🔐 *Brute Bank Order #{order.id} — {bank_name}*\n\n"
            f"⏱ *You have {BRUTE_CHECK_WINDOW} minutes to verify\\.*\n"
            f"After that, payment goes to the seller\\.\n\n"
            f"📸 Refund requires screenshot proof\\.\n"
            f"Moderation will decide all disputes\\.\n\n"
            f"🔑 *Your credentials:*\n{creds_lines}"
        ),
        reply_markup=_brute_result_keyboard(order.id),
        parse_mode="Markdown",
    )
    await callback.answer()
