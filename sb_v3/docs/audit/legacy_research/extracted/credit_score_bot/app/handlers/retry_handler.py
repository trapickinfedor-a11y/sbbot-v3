"""
Хэндлер для команды /retry.
"""

from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message

from ..services.retry_manager import retry_failed_jobs

router = Router()

@router.message(Command("retry"))
async def handle_retry_command(message: Message, bot: Bot):
    """Запускает повторную обработку ошибочных задач из последнего батча."""
    await message.answer("Инициирую повторную обработку ошибочных задач из последнего запуска...")
    await retry_failed_jobs(bot, message.chat.id)
