from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from main_bot.app.services.mirror_bot import MirrorBotService
from main_bot.app.keyboards.main_menu import get_main_menu_keyboard, get_bot_active_keyboard
from main_bot.app.constants.texts import BotTexts
from main_bot.app.utils.helpers import send_message_with_media

router = Router()

SUPPORTED_LANGS = ("en", "ru", "es", "zh")


def _language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇬🇧 English", callback_data="main_lang:en"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="main_lang:ru"),
        ],
        [
            InlineKeyboardButton(text="🇪🇸 Español", callback_data="main_lang:es"),
            InlineKeyboardButton(text="🇨🇳 中文", callback_data="main_lang:zh"),
        ],
    ])


@router.message(CommandStart())
async def start_handler(message: Message, mirror_service: MirrorBotService, state: FSMContext):
    user_bots = await mirror_service.get_user_bots(message.from_user.id)

    if user_bots:
        existing_bot = user_bots[0]
        bot_username = existing_bot.bot_username

        # Если username не сохранен, получаем его через API и обновляем в БД
        if not bot_username:
            try:
                from aiogram import Bot
                temp_bot = Bot(token=existing_bot.bot_token)
                bot_info = await temp_bot.get_me()
                bot_username = bot_info.username or "unknown_bot"
                await temp_bot.session.close()

                # Обновляем username в базе данных
                await mirror_service.update_bot_username(existing_bot.user_id, bot_username)
            except Exception:
                bot_username = "unknown_bot"

        bots_list = "\n".join(
            f"- [@{bot.bot_username}](https://t.me/{bot.bot_username})" for bot in user_bots if bot.bot_username
        ) or f"- [@{bot_username}](https://t.me/{bot_username})"
        text = (
            f"⚡️ **ONE — Access Confirmed**\n"
            f"**Ваших ботов:** {len(user_bots)}\n\n"
            f"{bots_list}\n\n"
            f"Вы можете открыть кабинет, посмотреть суммарную статистику или создать ещё одного бота."
        )
        await send_message_with_media(
            message,
            text,
            reply_markup=get_bot_active_keyboard(bot_username)
        )
    else:
        # New user — show language selection first
        fsm_data = await state.get_data()
        lang = fsm_data.get("language")
        if not lang:
            await message.answer(
                "🌍 <b>Choose your language / Выберите язык</b>",
                reply_markup=_language_keyboard(),
                parse_mode="HTML",
            )
        else:
            await send_message_with_media(
                message,
                BotTexts.START_NEW_USER,
                reply_markup=get_main_menu_keyboard()
            )


@router.callback_query(F.data.startswith("main_lang:"))
async def main_bot_language_callback(callback: CallbackQuery, state: FSMContext, mirror_service: MirrorBotService):
    lang = callback.data.split(":", 1)[1]
    if lang not in SUPPORTED_LANGS:
        lang = "en"

    await state.update_data(language=lang)

    try:
        await callback.message.delete()
    except Exception:
        pass

    user_bots = await mirror_service.get_user_bots(callback.from_user.id)
    if not user_bots:
        await send_message_with_media(
            callback.message,
            BotTexts.START_NEW_USER,
            reply_markup=get_main_menu_keyboard()
        )
    else:
        bot_username = user_bots[0].bot_username or "your_bot"
        await send_message_with_media(
            callback.message,
            BotTexts.START_NEW_USER,
            reply_markup=get_bot_active_keyboard(bot_username)
        )

    await callback.answer("✅ Language saved")
