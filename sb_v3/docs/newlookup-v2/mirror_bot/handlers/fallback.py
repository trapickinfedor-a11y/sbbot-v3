"""
Fallback обработчик для необработанных событий
"""
import logging
from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram import F

logger = logging.getLogger(__name__)

router = Router(name="fallback")


@router.message()
async def fallback_message_handler(message: Message):
    """Обработчик для всех необработанных сообщений"""
    logger.warning(f"❌ Unhandled message from user {message.from_user.id}: {message.text}")
    # Не отправляем ответ пользователю, просто логируем


@router.callback_query()
async def fallback_callback_handler(callback: CallbackQuery, texts):
    """Обработчик для всех необработанных callback_query"""
    logger.warning(f"❌ Unhandled callback from user {callback.from_user.id}: {callback.data}")
    
    # Если это confirm кнопка без состояния, показываем специальное сообщение
    if "confirm" in callback.data:
        await callback.answer(texts.PLEASE_START_PROCESS_AGAIN, show_alert=True)
    else:
        await callback.answer(texts.UNHANDLED_ACTION, show_alert=False)  # Минимальный ответ

