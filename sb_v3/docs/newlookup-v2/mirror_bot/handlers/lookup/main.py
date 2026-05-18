from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from mirror_bot.keyboards.inline import lookup_keyboard, phone_search_keyboard
from mirror_bot.middlewares.language import LanguageHelper
from mirror_bot.constants.language_loader import get_texts
from mirror_bot.constants.buttons_en import ButtonTexts
from mirror_bot.utils.message_utils import safe_edit_message
from mirror_bot.utils.media_library import resolve_bot_photo

router = Router()

LOOKUP_PHOTO = resolve_bot_photo("lookup", fallback_path="media/Lookup.jpg")


@router.message(F.text.in_(ButtonTexts.get_all_variants("SEARCH")))
async def lookup_main_handler(message: Message, texts, buttons):
    try:
        await message.answer_photo(
            photo=LOOKUP_PHOTO,
            caption=texts.LOOKUP_MAIN,
            reply_markup=lookup_keyboard(buttons)
        )
    except Exception:
        await message.answer(
            texts.LOOKUP_MAIN,
            reply_markup=lookup_keyboard(buttons)
        )


@router.callback_query(F.data == "back_lookup")
async def back_to_lookup_handler(callback: CallbackQuery, texts, buttons):
    # Для возврата в lookup всегда отправляем с фото
    try:
        await callback.message.delete()
        await callback.bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=LOOKUP_PHOTO,
            caption=texts.LOOKUP_MAIN,
            reply_markup=lookup_keyboard(buttons)
        )
    except Exception:
        # Fallback без фото
        await safe_edit_message(
            callback,
            texts.LOOKUP_MAIN,
            reply_markup=lookup_keyboard(buttons)
        )
    await callback.answer()


@router.callback_query(F.data == "lookup_phone")
async def phone_search_handler(callback: CallbackQuery, texts, buttons):
    await safe_edit_message(
        callback,
        texts.PHONE_SEARCH_HEADER,
        reply_markup=phone_search_keyboard(buttons)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("lookup_support"))
async def lookup_support_handler(callback: CallbackQuery, texts, buttons):
    """Обработчик для кнопки Lookup Support"""
    back_text = buttons.BACK
    
    # Определяем откуда пришел пользователь и выбираем соответствующий текст
    parts = callback.data.split(":")
    back_callback = "back_lookup"  # По умолчанию возврат в lookup
    support_text = texts.LOOKUP_SUPPORT_TEXT  # По умолчанию общий текст
    
    if len(parts) > 1:
        source = parts[1]
        # Если указан возвратный адрес (banks_main, accounts_main)
        back_callback = source
        
        # Выбираем соответствующий текст
        if source == "banks_main":
            support_text = texts.LOOKUP_SUPPORT_BANKS
        elif source == "accounts_main":
            support_text = texts.LOOKUP_SUPPORT_ACCOUNTS
    
    await safe_edit_message(
        callback,
        support_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=back_text, callback_data=back_callback)]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()

