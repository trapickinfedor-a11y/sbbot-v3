from __future__ import annotations

"""Mirror Bot — Fuzzy Search across the catalog (SellerBank items)."""
import logging
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database.models import SellerBank

logger = logging.getLogger(__name__)
router = Router(name="catalog_search")

MAX_RESULTS = 10


class CatalogSearchFSM(StatesGroup):
    waiting_query = State()


def _search_keyboard(results: list[SellerBank]) -> InlineKeyboardMarkup:
    buttons = []
    for bank in results[:MAX_RESULTS]:
        price = float(bank.buyer_price or bank.seller_price or 0)
        label = f"${price:.0f} · {bank.bank_name[:35]}"
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"view_bank:{bank.id}",
        )])
    buttons.append([InlineKeyboardButton(text="🔍 New Search", callback_data="catalog_search_start")])
    buttons.append([InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _fuzzy_score(query: str, bank: SellerBank) -> float:
    """Calculate fuzzy match score for a bank against the query."""
    from rapidfuzz import fuzz
    q = query.lower()
    name = (bank.bank_name or "").lower()
    state = (bank.state or "").lower()
    category = (bank.category or "").lower()
    desc = ((bank.description or "")[:200]).lower()

    text = f"{name} {state} {category}"
    # Use token_set_ratio for better partial matching
    return max(
        fuzz.token_set_ratio(q, text),
        fuzz.partial_ratio(q, name) * 0.9,
        fuzz.partial_ratio(q, text) * 0.8,
    )


async def _do_fuzzy_search(
    session: AsyncSession,
    query: str,
    mirror_bot_id: int,
    min_score: float = 50.0,
) -> list[SellerBank]:
    """Search SellerBank items using fuzzy matching on name/state/category."""
    result = await session.execute(
        select(SellerBank).where(
            SellerBank.is_active == True,
            SellerBank.stock_count > 0,
            SellerBank.moderation_status == "approved",
        ).limit(500)
    )
    banks = list(result.scalars().all())

    scored = [(bank, _fuzzy_score(query, bank)) for bank in banks]
    scored.sort(key=lambda x: -x[1])
    return [bank for bank, score in scored if score >= min_score][:MAX_RESULTS]


# ── Handlers ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "catalog_search_start")
async def cb_catalog_search_start(callback: CallbackQuery, state: FSMContext, **kwargs):
    await state.set_state(CatalogSearchFSM.waiting_query)
    await callback.message.answer(
        "🔍 <b>Smart Catalog Search</b>\n\n"
        "Type a product name, bank, state, or any keyword.\n"
        "<i>Example: 'chase ca' or 'bank of america texas'</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="back_main")]
        ])
    )
    await callback.answer()


@router.message(CatalogSearchFSM.waiting_query)
async def fsm_catalog_search_query(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    mirror_bot_id: int = 0,
    **kwargs,
):
    query = (message.text or "").strip()
    if len(query) < 2:
        await message.answer("❌ Query too short. Please enter at least 2 characters.")
        return

    await state.clear()
    results = await _do_fuzzy_search(session, query, mirror_bot_id)

    if not results:
        await message.answer(
            f"❌ No results found for: <b>{query}</b>\n\n"
            f"Try different keywords or browse the catalog.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔍 Try Again", callback_data="catalog_search_start")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")],
            ])
        )
        return

    await message.answer(
        f"🔍 <b>Search results for:</b> <i>{query}</i>\n\n"
        f"Found <b>{len(results)}</b> item(s). Tap to view:",
        parse_mode="HTML",
        reply_markup=_search_keyboard(results),
    )


@router.message(F.text.startswith("/search"))
async def cmd_search(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    mirror_bot_id: int = 0,
    **kwargs,
):
    parts = (message.text or "").split(None, 1)
    if len(parts) < 2 or not parts[1].strip():
        await state.set_state(CatalogSearchFSM.waiting_query)
        await message.answer(
            "🔍 Enter your search query:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancel", callback_data="back_main")]
            ])
        )
        return

    query = parts[1].strip()
    results = await _do_fuzzy_search(session, query, mirror_bot_id)
    if not results:
        await message.answer(f"No results for: <b>{query}</b>", parse_mode="HTML")
        return
    await message.answer(
        f"🔍 <b>Results for:</b> <i>{query}</i> ({len(results)} found)",
        parse_mode="HTML",
        reply_markup=_search_keyboard(results),
    )
