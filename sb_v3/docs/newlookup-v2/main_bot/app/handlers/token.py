import re
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from main_bot.app.services.mirror_bot import MirrorBotService
from main_bot.app.keyboards.main_menu import get_bot_active_keyboard
from main_bot.app.constants.texts import BotTexts
from main_bot.app.constants.config import AppConstants
from main_bot.app.utils.helpers import send_message_with_media

router = Router()

TOKEN_PATTERN = re.compile(AppConstants.TOKEN_PATTERN)

@router.message(lambda message: message.text and TOKEN_PATTERN.match(message.text))
async def token_handler(message: Message, mirror_service: MirrorBotService):
    await message.answer(BotTexts.VALIDATING_TOKEN)
    
    success, result = await mirror_service.start_mirror_bot(
        user_id=message.from_user.id,
        bot_token=message.text
    )
    
    if success:
        bot_username = result
        text = BotTexts.bot_confirmed(bot_username)
        await send_message_with_media(
            message,
            text,
            reply_markup=get_bot_active_keyboard(bot_username)
        )
    else:
        await message.answer(result)

