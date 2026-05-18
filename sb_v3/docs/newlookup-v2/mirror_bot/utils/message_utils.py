"""
Утилиты для работы с сообщениями
"""
import logging
from aiogram.types import CallbackQuery, InlineKeyboardMarkup

logger = logging.getLogger(__name__)


async def safe_edit_message(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup = None,
    parse_mode: str = None
):
    """Edit or re-send the message associated with a callback.

    Tries in order:
    1. edit_caption  (if the message has a photo)
    2. edit_text     (plain text message)
    3. delete + send_message  (fallback when edit is not possible,
       e.g. message is too old or content-type changed)
    """
    try:
        if callback.message.photo:
            await callback.message.edit_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        else:
            await callback.message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
    except Exception as edit_err:
        try:
            chat_id = callback.message.chat.id
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        except Exception as fallback_error:
            logger.error("Failed to edit/send message: %s", fallback_error)


async def safe_answer_callback(callback: CallbackQuery, text: str = None, show_alert: bool = False):
    """Безопасный ответ на callback_query"""
    try:
        await callback.answer(text=text, show_alert=show_alert)
    except Exception as e:
        if "query is too old" in str(e) or "message is not modified" in str(e):
            logger.debug("Callback query too old or message not modified: %s", e)
        else:
            logger.error("Error answering callback query: %s", e)

