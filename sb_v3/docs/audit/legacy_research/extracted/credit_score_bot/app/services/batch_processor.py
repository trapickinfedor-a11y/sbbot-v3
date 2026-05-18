"""
Сервис для управления массовыми (batch) задачами.

Отвечает за:
- Хранение состояния всех задач в батче.
- Генерацию CSV-отчета.
- Отправку промежуточных и финальных отчетов в Telegram.
"""

import asyncio
import csv
import logging
import time
from pathlib import Path
from typing import Dict, List

from aiogram import Bot
from cs_module import JobRequest, JobResult

logger = logging.getLogger(__name__)

# --- Batch State Manager ---

class BatchState:
    """Хранит состояние одного массового запуска."""

    def __init__(self, batch_id: str, total_jobs: int, chat_id: int):
        self.batch_id = batch_id
        self.chat_id = chat_id
        self.total_jobs = total_jobs
        self.start_time = time.time()
        self.results: Dict[str, JobResult] = {}
        self.status_message_id: int = None
        self.completed_jobs = 0
        self.success_count = 0
        self.failed_count = 0
        self.is_finished = False

    def add_result(self, result: JobResult):
        """Добавляет результат задачи и обновляет счетчики."""
        if result.job_id not in self.results:
            self.completed_jobs += 1
            if result.is_success():
                self.success_count += 1
            else:
                # Считаем FAILED только если это не ожидание SSN
                if not result.needs_ssn:
                    self.failed_count += 1
        self.results[result.job_id] = result

    def get_progress_text(self) -> str:
        """Генерирует текст для статус-сообщения."""
        elapsed = time.time() - self.start_time
        progress = self.completed_jobs / self.total_jobs * 100
        
        text = (
            f"<b>Массовая обработка (Batch ID: <code>{self.batch_id}</code>)</b>\n\n"
            f"- <b>Прогресс:</b> {self.completed_jobs} / {self.total_jobs} ({progress:.1f}%)\n"
            f"- ✅ <b>Успешно:</b> {self.success_count}\n"
            f"- ❌ <b>Ошибки:</b> {self.failed_count}\n"
            f"- ⏳ <b>Время:</b> {elapsed:.0f} сек.\n\n"
        )
        if self.is_finished:
            text += "<b>Статус:</b> Завершено. Отчет генерируется..."
        else:
            text += "<b>Статус:</b> В работе..."
        return text

# Глобальный словарь для хранения активных батчей
# {chat_id: BatchState}
active_batches: Dict[int, BatchState] = {}

# --- CSV Report --- 

def generate_csv_report(batch: BatchState) -> Path:
    """Генерирует CSV-отчет по результатам батча."""
    report_dir = Path("./data/reports")
    report_dir.mkdir(exist_ok=True)
    report_path = report_dir / f"report_{batch.batch_id}.csv"

    headers = [
        "job_id", "status", "credit_score", "error",
        "source", "worker_id", "duration_seconds"
    ]

    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for result in batch.results.values():
            writer.writerow({
                "job_id": result.job_id,
                "status": result.status.name,
                "credit_score": result.credit_score or "",
                "error": result.error or "",
                "source": result.source or "",
                "worker_id": result.worker_id or "",
                "duration_seconds": result.duration_seconds or "",
            })
    
    logger.info(f"CSV report generated: {report_path}")
    return report_path

# --- Status Updater ---

async def update_status_message(bot: Bot, batch: BatchState):
    """Обновляет сообщение со статусом выполнения."""
    if not batch.status_message_id:
        return
    try:
        await bot.edit_message_text(
            chat_id=batch.chat_id,
            message_id=batch.status_message_id,
            text=batch.get_progress_text(),
        )
    except Exception as e:
        # Сообщение могло быть удалено, или бот не может его отредактировать
        logger.warning(f"Could not edit status message for batch {batch.batch_id}: {e}")
