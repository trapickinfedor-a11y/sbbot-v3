from aiogram import Router
from aiogram.types import Message

router = Router()

@router.message()
async def echo_handler(message: Message):
    # Этот handler не должен отвечать - fallback уже обрабатывает
    pass

