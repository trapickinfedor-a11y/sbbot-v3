"""Справка — i18n"""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.database.models import Marketer
from marketer_bot.constants.language_loader import get_texts

router = Router(name="marketer_help")


@router.message(Command("help"))
async def cmd_help(message: Message, session: AsyncSession, texts=None, **kwargs):
    result = await session.execute(
        select(Marketer).where(Marketer.telegram_id == message.from_user.id)
    )
    marketer = result.scalar_one_or_none()
    t = texts or get_texts(marketer.language if marketer else None)
    await message.answer(t.HELP_TEXT)
