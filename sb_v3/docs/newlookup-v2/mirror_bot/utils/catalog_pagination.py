"""
Reusable paginated inline keyboards for mirror_bot catalog sections.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def paginated_keyboard(
    items: Sequence[Any],
    page: int,
    items_per_page: int,
    item_text_fn: Callable[[Any], str],
    item_callback_fn: Callable[[Any], str],
    nav_prefix: str,
    back_callback: str,
    sort_callback: str | None = None,
    current_sort: str = "default",
    extra_top_rows: list[list[InlineKeyboardButton]] | None = None,
    nav_extra: str = "",
) -> InlineKeyboardMarkup:
    """
    Build InlineKeyboardMarkup with item rows + prev/next + optional sort + back.

    :param nav_prefix: callback prefix for page navigation, e.g. "banks_avail_page"
           callbacks: {nav_prefix}:{page}{nav_extra}  (nav_extra often empty or :extra)
    :param sort_callback: if set, one button toggles sort; data = sort_callback
    """
    items = list(items)
    total = len(items)
    total_pages = max(1, (total + items_per_page - 1) // items_per_page)
    page = max(0, min(page, total_pages - 1))
    start = page * items_per_page
    chunk = items[start : start + items_per_page]

    rows: list[list[InlineKeyboardButton]] = []
    if extra_top_rows:
        rows.extend(extra_top_rows)

    for it in chunk:
        rows.append(
            [
                InlineKeyboardButton(
                    text=item_text_fn(it),
                    callback_data=item_callback_fn(it),
                )
            ]
        )

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="⬅️ Prev",
                callback_data=f"{nav_prefix}:{page - 1}{nav_extra}",
            )
        )
    nav.append(
        InlineKeyboardButton(
            text=f"📄 {page + 1}/{total_pages}",
            callback_data="page_info",
        )
    )
    if page < total_pages - 1:
        nav.append(
            InlineKeyboardButton(
                text="Next ➡️",
                callback_data=f"{nav_prefix}:{page + 1}{nav_extra}",
            )
        )
    if nav:
        rows.append(nav)

    if sort_callback:
        sort_label = "💲 Price ↑" if current_sort == "price_asc" else "💲 Price ↓" if current_sort == "price_desc" else "💲 Sort"
        rows.append(
            [
                InlineKeyboardButton(
                    text=sort_label,
                    callback_data=sort_callback,
                )
            ]
        )

    rows.append([InlineKeyboardButton(text="⬅️ Back", callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def clamp_page(page: int, total_items: int, items_per_page: int) -> int:
    total_pages = max(1, (max(0, total_items) + items_per_page - 1) // items_per_page)
    return max(0, min(page, total_pages - 1))
