"""
Хэндлеры для пошагового заполнения анкеты (FSM).
"""

import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from ..fsm.states import Form
from ..keyboards import get_confirm_keyboard, get_cancel_keyboard
from ..messages import format_summary_message
from ..services.worker_pool import pool
from cs_module import JobRequest

logger = logging.getLogger(__name__)
router = Router()

# --- Начало анкетирования ---
@router.message(Command("check"))
async def start_form(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("✍️ Начинаем сбор данных. Введите имя (First Name):", reply_markup=get_cancel_keyboard())
    await state.set_state(Form.first_name)

# --- Отмена ---
@router.callback_query(F.data == "cancel_form")
async def cancel_form(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Заполнение анкеты отменено.")
    await callback.answer()

# --- Шаги FSM ---

@router.message(StateFilter(Form.first_name))
async def process_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await message.answer("Введите фамилию (Last Name):", reply_markup=get_cancel_keyboard())
    await state.set_state(Form.last_name)

@router.message(StateFilter(Form.last_name))
async def process_last_name(message: Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    await message.answer("Введите улицу и дом (Street):", reply_markup=get_cancel_keyboard())
    await state.set_state(Form.street)

@router.message(StateFilter(Form.street))
async def process_street(message: Message, state: FSMContext):
    await state.update_data(street=message.text)
    await message.answer("Введите город (City):", reply_markup=get_cancel_keyboard())
    await state.set_state(Form.city)

@router.message(StateFilter(Form.city))
async def process_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Введите штат (State, 2 буквы, например, CA):", reply_markup=get_cancel_keyboard())
    await state.set_state(Form.state)

@router.message(StateFilter(Form.state))
async def process_state(message: Message, state: FSMContext):
    if len(message.text) != 2 or not message.text.isalpha():
        await message.answer("Ошибка. Введите 2 буквы штата (например, CA):", reply_markup=get_cancel_keyboard())
        return
    await state.update_data(state=message.text.upper())
    await message.answer("Введите ZIP-код:", reply_markup=get_cancel_keyboard())
    await state.set_state(Form.zip_code)

@router.message(StateFilter(Form.zip_code))
async def process_zip_code(message: Message, state: FSMContext):
    await state.update_data(zip_code=message.text)
    await message.answer("Введите дату рождения (MM/DD/YYYY):", reply_markup=get_cancel_keyboard())
    await state.set_state(Form.dob)

@router.message(StateFilter(Form.dob))
async def process_dob(message: Message, state: FSMContext):
    await state.update_data(dob=message.text)
    await message.answer("Введите годовой доход (Annual Income, например, 35000):", reply_markup=get_cancel_keyboard())
    await state.set_state(Form.annual_income)

@router.message(StateFilter(Form.annual_income))
async def process_annual_income(message: Message, state: FSMContext):
    await state.update_data(annual_income=message.text)
    
    # Показываем сводку для подтверждения
    data = await state.get_data()
    summary_text = format_summary_message(data)
    await message.answer(summary_text, reply_markup=get_confirm_keyboard())
    await state.set_state(Form.confirm)

# --- Подтверждение и отправка ---

@router.callback_query(StateFilter(Form.confirm), F.data == "confirm_and_send")
async def confirm_and_send(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()

    # Создаем JobRequest
    job = JobRequest(
        telegram_chat_id=callback.message.chat.id,
        telegram_message_id=callback.message.message_id,
        telegram_user_id=callback.from_user.id,
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
        street=data.get("street"),
        city=data.get("city"),
        state=data.get("state"),
        zip_code=data.get("zip_code"),
        dob=data.get("dob"),
        annual_income=data.get("annual_income"),
    )

    # Отправляем в пул воркеров
    job_id = await pool.submit(job)
    logger.info(f"Job {job_id} submitted for user {callback.from_user.id}")

    await callback.message.edit_text(f"⏳ Запрос принят в обработку. Job ID: <code>{job_id}</code>. Ожидайте результат.")
    await callback.answer()

@router.callback_query(StateFilter(Form.confirm), F.data == "restart_form")
async def restart_form(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Начинаем заново.")
    await start_form(callback.message, state)
    await callback.answer()
