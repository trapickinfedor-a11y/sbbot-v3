from __future__ import annotations
"""
Хэндлер старта и авторизации
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from support_bot.services.access_service import SupportBotActor
from support_bot.keyboards.inline import admin_menu_keyboard, back_to_menu_keyboard

router = Router(name="start")

SUPPORTED_LANGS = ("en", "ru", "es", "zh")


def _language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇬🇧 English", callback_data="support_lang:en"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="support_lang:ru"),
        ],
        [
            InlineKeyboardButton(text="🇪🇸 Español", callback_data="support_lang:es"),
            InlineKeyboardButton(text="🇨🇳 中文", callback_data="support_lang:zh"),
        ],
    ])


def _admin_commands_text(actor: SupportBotActor) -> str:
    commands: list[str] = []
    if actor.can_add_balance:
        commands.append("• <code>/add_balance [user_id] [amount]</code> - manual balance top-up")
    if actor.can_moderate_sellers:
        commands.append("• <code>/seller_moderation</code> - seller products moderation")
    commands.append("• <code>/start</code> - open this menu again")
    return "\n".join(commands)


async def _render_home(message_or_callback, *, first_name: str, actor: SupportBotActor | None = None):
    if actor and actor.is_admin_like:
        text = (
            f"👋 <b>Welcome, {first_name}!</b>\n\n"
            f"🔐 <b>Role:</b> {actor.role}\n"
            f"🆔 <b>Telegram ID:</b> <code>{actor.telegram_id}</code>\n\n"
            f"<b>Available commands:</b>\n{_admin_commands_text(actor)}"
        )
        keyboard = admin_menu_keyboard(
            can_add_balance=actor.can_add_balance,
            can_moderate=actor.can_moderate_sellers,
            can_manage_finance=actor.can_manage_finance,
            can_upload_catalogs=actor.can_upload_catalogs,
        )
    else:
        text = (
            "❌ <b>Access Denied</b>\n\n"
            "This bot is reserved for support staff and admins."
        )
        keyboard = None

    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text, reply_markup=keyboard)
    else:
        await message_or_callback.message.edit_text(text, reply_markup=keyboard)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, support_bot_actor: SupportBotActor | None = None):
    """Команда /start"""
    # Show language selection if the user has never set a language preference
    fsm_data = await state.get_data()
    if not fsm_data.get("language"):
        await message.answer(
            "🌍 <b>Choose your language / Выберите язык</b>",
            reply_markup=_language_keyboard(),
            parse_mode="HTML",
        )
        return

    await _render_home(
        message,
        first_name=message.from_user.first_name,
        actor=support_bot_actor,
    )


@router.callback_query(F.data.startswith("support_lang:"))
async def support_bot_language_callback(
    callback: CallbackQuery,
    state: FSMContext,
    support_bot_actor: SupportBotActor | None = None,
):
    lang = callback.data.split(":", 1)[1]
    if lang not in SUPPORTED_LANGS:
        lang = "en"

    await state.update_data(language=lang)

    try:
        await callback.message.delete()
    except Exception:
        pass

    await _render_home(
        callback,
        first_name=callback.from_user.first_name,
        actor=support_bot_actor,
    )
    await callback.answer("✅ Language saved")


BOT_DESCRIPTION = """📋 <b>Описание Support Bot</b>

<b>Назначение:</b>
Бот для модерации, поддержки и администрирования.

<b>Основные функции:</b>
• Seller moderation — модерация товаров продавцов
• Seller order support — поддержка заказов продавцов
• Manual balance tools — ручное пополнение баланса
• Accountant panel — управление выплатами (seller/marketer/worker)
• Uploader panel — загрузка каталогов товаров

<b>Доступные роли:</b>
• Support — проверка баланса пользователей
• Moderator — модерация товаров, установка цен
• Finance/Accountant — управление выплатами
• Uploader — загрузка каталогов
• Admin/Owner — полный доступ"""


@router.callback_query(F.data == "bot_description")
async def callback_bot_description(callback: CallbackQuery, session: AsyncSession, support_bot_actor: SupportBotActor | None = None):
    """Показать описание бота"""
    if not support_bot_actor:
        await callback.answer("Access denied", show_alert=True)
        return
    await callback.message.edit_text(
        BOT_DESCRIPTION,
        reply_markup=back_to_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext, support_bot_actor: SupportBotActor | None = None):
    """Возврат в главное меню"""
    await state.clear()

    if not support_bot_actor:
        await callback.answer("Access denied", show_alert=True)
        return

    await _render_home(
        callback,
        first_name=callback.from_user.first_name,
        actor=support_bot_actor,
    )
    await callback.answer()
