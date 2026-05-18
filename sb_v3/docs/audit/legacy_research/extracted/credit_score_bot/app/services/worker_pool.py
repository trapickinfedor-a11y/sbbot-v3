"""
Модуль для инициализации и управления пулом воркеров cs_module.

Версия 2: Добавлена логика для обработки результатов массовых задач.
"""

import logging
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile

from cs_module import WorkerPool, WorkerPoolConfig, JobResult, JobStatus, ssn_flow
from ..config import settings
from cs_module.workers.cs_worker import CreditScoreWorker
from ..fsm.states import SSN
from .batch_processor import active_batches, generate_csv_report, update_status_message

logger = logging.getLogger(__name__)

# Глобальный словарь для сопоставления chat_id и job_id при ожидании SSN
pending_ssn_jobs = {}

async def on_result_callback(result: JobResult, bot: Bot, storage):
    """
    Callback, который вызывается, когда воркер завершает задачу.
    Отправляет результат пользователю или обрабатывает его в рамках батча.
    """
    chat_id = result.telegram_chat_id
    logger.info(f"Received result for job {result.job_id} for chat {chat_id}. Status: {result.status.name}")

    # --- Логика для массовых задач (batch) ---
    if chat_id in active_batches:
        batch = active_batches[chat_id]
        batch.add_result(result)

        # Обновляем статус-сообщение
        await update_status_message(bot, batch)

        # Если все задачи в батче завершены
        if batch.completed_jobs >= batch.total_jobs:
            batch.is_finished = True
            logger.info(f"Batch {batch.batch_id} finished for chat {chat_id}.")
            await update_status_message(bot, batch) # Финальное обновление статуса

            # Генерируем и отправляем CSV-отчет
            report_path = generate_csv_report(batch)
            await bot.send_document(
                chat_id=chat_id,
                document=FSInputFile(report_path),
                caption=f"✅ Отчет по массовой задаче <code>{batch.batch_id}</code> готов."
            )
            # Можно удалить батч из активных или оставить для ретраев
            # del active_batches[chat_id]
        return # В массовом режиме не отправляем одиночные сообщения

    # --- Логика для одиночных задач (FSM) ---
    if result.status == JobStatus.WAITING_SSN:
        pending_ssn_jobs[chat_id] = result.job_id
        user_fsm_key = f"{bot.id}:{chat_id}:{chat_id}"
        user_context = FSMContext(storage=storage, key=user_fsm_key)
        await user_context.set_state(SSN.waiting_for_ssn)
        await bot.send_message(
            chat_id,
            "🔑 Для продолжения нужен ваш SSN. Пожалуйста, введите его в формате <code>XXX-XX-XXXX</code>."
        )

    elif result.status == JobStatus.SUCCESS:
        await bot.send_message(
            chat_id,
            f"✅ <b>Кредитный скор получен!</b>\n\n"
            f"- <b>Скор:</b> <code>{result.credit_score}</code>\n"
            f"- <b>Источник:</b> {result.source}\n"
            f"- <b>Время выполнения:</b> {result.duration_seconds} сек."
        )

    elif result.status == JobStatus.FAILED:
        error_message = result.error or "Неизвестная ошибка"
        await bot.send_message(
            chat_id,
            f"❌ <b>Не удалось получить кредитный скор.</b>\n\n"
            f"<b>Причина:</b> {error_message}"
        )

# Создание конфига для пула
pool_config = WorkerPoolConfig(
    proxy_host=settings.PROXY_HOST,
    proxy_port=settings.PROXY_PORT,
    proxy_username=settings.PROXY_USERNAME,
    proxy_password=settings.PROXY_PASSWORD,
    proxy_type="http",
    proxy_country="us",
    rotate_on_success=settings.WORKER_ROTATE_ON_SUCCESS,
    num_workers=settings.WORKER_COUNT,
    headless=settings.WORKER_HEADLESS,
    screenshot_dir=settings.WORKER_SCREENSHOT_DIR,
)

# Глобальный экземпляр пула
pool: Optional[WorkerPool] = None

async def start_worker_pool(bot: Bot, dp):
    logger.info("Starting worker pool...")
    global pool
    pool_config.on_result = lambda result: on_result_callback(result, bot, dp.storage)
    pool = WorkerPool(pool_config, bot_instance=bot) # Pass bot instance here
    await pool.start()
    logger.info("Worker pool started.")

async def stop_worker_pool():
    logger.info("Stopping worker pool...")
    await pool.stop()
    logger.info("Worker pool stopped.")
