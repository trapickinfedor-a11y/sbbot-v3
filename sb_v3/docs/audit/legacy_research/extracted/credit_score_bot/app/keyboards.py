"""
Фабрики для создания inline-клавиатур.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения данных."""
    buttons = [
        [InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_and_send")],
        [InlineKeyboardButton(text="🔄 Начать заново", callback_data="restart_form")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для отмены заполнения."""
    buttons = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_form")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
