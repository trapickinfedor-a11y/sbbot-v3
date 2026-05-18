"""
Хэндлер для массовой загрузки и обработки профилей.
"""

import logging
import time
from typing import List

from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message

from cs_module import JobRequest
from ..utils import parse_bulk_text
from ..services.batch_processor import BatchState, active_batches, update_status_message
from ..services.retry_manager import original_jobs_store
from ..services.worker_pool import pool

logger = logging.getLogger(__name__)
router = Router()


async def start_batch_processing(bot: Bot, chat_id: int, jobs: List[JobRequest]):
    """
    Общая функция для запуска массовой обработки.
    Используется как для новых задач, так и для повторных.
    """
    if not jobs:
        await bot.send_message(chat_id, "Не найдено ни одного профиля для обработки.")
        return

    batch_id = f"{chat_id}_{int(time.time())}"
    total_jobs = len(jobs)
    batch = BatchState(batch_id, total_jobs, chat_id)
    active_batches[chat_id] = batch

    # Сохраняем оригинальные джобы для возможности ретрая
    original_jobs_store[batch_id] = {job.job_id: job for job in jobs}

    # Отправляем первоначальное статус-сообщение
    status_msg = await bot.send_message(chat_id, batch.get_progress_text())
    batch.status_message_id = status_msg.message_id

    logger.info(f"Starting batch {batch_id} with {total_jobs} jobs.")

    # Отправляем все задачи в пул
    for job in jobs:
        await pool.submit(job)


@router.message(Command("bulk"))
async def handle_bulk_command(message: Message):
    """Инструкция по использованию /bulk."""
    await message.answer(
        "<b>Режим массовой загрузки</b>\n\n"
        "Вставьте текст со списком профилей. Каждый профиль должен состоять из 7 строк:\n"
        "1. Имя\n"
        "2. Фамилия\n"
        "3. Адрес\n"
        "4. Город\n"
        "5. Штат (2 буквы)\n"
        "6. ZIP-код\n"
        "7. Дата рождения (MM/DD/YYYY)\n\n"
        "Профили разделяются пустой строкой. После отправки текста бот начнет обработку."
    )


@router.message(lambda msg: not msg.text.startswith("/"))
async def handle_bulk_text(message: Message, bot: Bot):
    """
    Обрабатывает сообщение с текстом, если это не команда.
    Парсит его и запускает массовую обработку.
    """
    # Проверяем, не активна ли уже задача для этого чата
    if message.chat.id in active_batches and not active_batches[message.chat.id].is_finished:
        await message.reply("Дождитесь завершения текущей массовой обработки, прежде чем начинать новую.")
        return

    parsed_profiles = parse_bulk_text(message.text)

    if not parsed_profiles:
        await message.reply("Не удалось распознать профили в тексте. Проверьте формат и попробуйте снова.")
        return

    # Создаем список JobRequest
    jobs = [
        JobRequest(
            telegram_chat_id=message.chat.id,
            telegram_message_id=message.message_id,
            telegram_user_id=message.from_user.id,
            **profile_data
        )
        for profile_data in parsed_profiles
    ]

    await start_batch_processing(bot, message.chat.id, jobs)
