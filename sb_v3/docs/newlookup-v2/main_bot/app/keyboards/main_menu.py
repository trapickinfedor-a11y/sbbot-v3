from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from main_bot.app.constants.config import AppConstants

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Личный кабинет", callback_data="owner_cabinet")],
        [InlineKeyboardButton(text="🌐 ACTUAL LINKS 🌐", url=AppConstants.LINKS["ACTUAL"])],
        [InlineKeyboardButton(text="🧵 WWH 🧵", url=AppConstants.LINKS["WWH"])],
        [InlineKeyboardButton(text="🗂 INSTRUCTIONS 🗂", url=AppConstants.LINKS["INSTRUCTIONS"])]
    ])

def get_bot_active_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Личный кабинет", callback_data="owner_cabinet")],
        [InlineKeyboardButton(text="➕ Создать ещё бота", callback_data="owner_create_bot")],
        [InlineKeyboardButton(text="🌐 ACTUAL LINKS 🌐", url=AppConstants.LINKS["ACTUAL"])],
        [InlineKeyboardButton(text=f"👉 Open your bot → @{bot_username}", url=f"https://t.me/{bot_username}")]
    ])

