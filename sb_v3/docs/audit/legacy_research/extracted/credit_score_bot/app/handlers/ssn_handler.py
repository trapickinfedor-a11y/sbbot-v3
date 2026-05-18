"""
Хэндлер для обработки ввода SSN от пользователя.
"""

import logging
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ..fsm.states import SSN
from ..services.worker_pool import pending_ssn_jobs
from cs_module import ssn_flow

logger = logging.getLogger(__name__)
router = Router()

@router.message(StateFilter(SSN.waiting_for_ssn))
async def process_ssn_input(message: Message, state: FSMContext):
    chat_id = message.chat.id
    ssn_input = message.text

    # Находим job_id, который мы сохранили ранее
    job_id = pending_ssn_jobs.get(chat_id)

    if not job_id:
        await message.answer("Произошла ошибка: не найден связанный запрос. Попробуйте начать заново с /check.")
        await state.clear()
        return

    # Передаем SSN в cs_module
    # ssn_flow сам валидирует формат
    success = ssn_flow.provide_ssn(job_id, ssn_input)

    if success:
        logger.info(f"SSN provided for job {job_id}. Resuming...")
        await message.answer("✅ SSN принят. Возобновляем обработку, ожидайте...")
        # Убираем пользователя из словаря ожидания и сбрасываем состояние
        del pending_ssn_jobs[chat_id]
        await state.clear()
    else:
        # Если формат неверный, ssn_flow вернет False
        await message.answer("❌ Неверный формат SSN. Пожалуйста, введите в формате <code>XXX-XX-XXXX</code>.")
