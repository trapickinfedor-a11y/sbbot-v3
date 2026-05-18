"""
Сервис для управления повторной отправкой ошибочных задач.
"""

import logging
from typing import Dict, List

from aiogram import Bot
from cs_module import JobRequest, JobStatus

from .batch_processor import BatchState, active_batches
from .worker_pool import pool

logger = logging.getLogger(__name__)

# Хранилище оригинальных JobRequest для возможности повторной отправки
# {batch_id: {job_id: JobRequest}}
original_jobs_store: Dict[str, Dict[str, JobRequest]] = {}

async def retry_failed_jobs(bot: Bot, chat_id: int):
    """
    Находит последний завершенный батч для чата и перезапускает все ошибочные задачи.
    """
    batch = active_batches.get(chat_id)
    if not batch or not batch.is_finished:
        await bot.send_message(chat_id, "Нет завершенных массовых задач для повтора.")
        return

    if not batch.failed_count:
        await bot.send_message(chat_id, "В последней задаче не было ошибок. Нечего повторять.")
        return

    logger.info(f"Retrying {batch.failed_count} failed jobs for batch {batch.batch_id}")

    original_jobs = original_jobs_store.get(batch.batch_id, {})
    jobs_to_retry: List[JobRequest] = []

    for job_id, result in batch.results.items():
        if result.status == JobStatus.FAILED:
            original_job = original_jobs.get(job_id)
            if original_job:
                # Создаем новый JobRequest на основе старого, чтобы получить новый job_id
                # и сбросить счетчики внутренних ретраев в cs_module
                new_job = JobRequest(
                    telegram_chat_id=original_job.telegram_chat_id,
                    telegram_message_id=original_job.telegram_message_id, # Можно обновить на новое сообщение
                    telegram_user_id=original_job.telegram_user_id,
                    first_name=original_job.first_name,
                    last_name=original_job.last_name,
                    street=original_job.street,
                    city=original_job.city,
                    state=original_job.state,
                    zip_code=original_job.zip_code,
                    dob=original_job.dob,
                    annual_income=original_job.annual_income,
                    # SSN не переносим, т.к. WAITING_SSN не считается ошибкой
                )
                jobs_to_retry.append(new_job)

    if not jobs_to_retry:
        await bot.send_message(chat_id, "Не удалось найти данные для повторной отправки.")
        return

    # Запускаем новую массовую обработку только для ошибочных задач
    from .bulk_handler import start_batch_processing # Избегаем циклического импорта
    await start_batch_processing(bot, chat_id, jobs_to_retry)
