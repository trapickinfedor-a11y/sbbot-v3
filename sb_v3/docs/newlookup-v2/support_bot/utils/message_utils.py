"""
Утилиты для работы с сообщениями
"""

from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
import logging

logger = logging.getLogger(__name__)


async def safe_edit_message(callback: CallbackQuery, text: str, reply_markup=None):
    """
    Безопасное редактирование сообщения с fallback на новое сообщение
    
    Args:
        callback: CallbackQuery объект
        text: Новый текст сообщения
        reply_markup: Клавиатура (опционально)
    """
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Сообщение не изменилось, просто отвечаем на callback
            logger.debug(f"Message not modified for callback {callback.id}")
        else:
            # Другая ошибка, отправляем новое сообщение
            logger.warning(f"Failed to edit message: {e}")
            await callback.message.answer(text, reply_markup=reply_markup)
    except Exception as e:
        # Любая другая ошибка, отправляем новое сообщение
        logger.error(f"Unexpected error editing message: {e}")
        await callback.message.answer(text, reply_markup=reply_markup)


async def safe_answer_callback(callback: CallbackQuery, text: str = None, show_alert: bool = False):
    """
    Безопасный ответ на callback query
    
    Args:
        callback: CallbackQuery объект
        text: Текст уведомления (опционально)
        show_alert: Показать как alert (опционально)
    """
    try:
        await callback.answer(text=text, show_alert=show_alert)
    except Exception as e:
        logger.error(f"Failed to answer callback: {e}")
