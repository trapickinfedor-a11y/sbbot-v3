from __future__ import annotations

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from mirror_bot.constants.buttons_en import ButtonTexts


def main_menu_keyboard(menu_categories: list[dict], counts: dict | None = None) -> ReplyKeyboardMarkup:
    """Главная клавиатура меню, построенная из БД."""
    counts = counts or {}
    rows: dict[int, list[KeyboardButton]] = {}

    for category in menu_categories:
        row = rows.setdefault(int(category.get("row_index") or 0), [])
        count_key = category.get("count_key")
        display_text = category.get("display_text") or category.get("code") or "Category"
        if count_key:
            display_text = ButtonTexts.with_count(display_text, counts.get(count_key))
        row.append(KeyboardButton(text=display_text))

    keyboard = [rows[row_index] for row_index in sorted(rows)]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
    )
