from typing import Optional
from aiogram.types import Message, FSInputFile
from aiogram.types import InlineKeyboardMarkup
from main_bot.app.config import config

async def send_message_with_media(
    message: Message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: str = "Markdown"
):
    if config.video_file_exists:
        video = FSInputFile(config.media_video_path)
        await message.answer_video(
            video=video,
            caption=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    else:
        await message.answer(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )

