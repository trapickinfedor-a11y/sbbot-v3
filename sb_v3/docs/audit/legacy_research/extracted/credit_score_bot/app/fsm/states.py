"""
Определение состояний для машины состояний (FSM) aiogram.

Состояния используются для пошагового сбора данных от пользователя.
"""

from aiogram.fsm.state import State, StatesGroup

class Form(StatesGroup):
    first_name = State()       # Имя
    last_name = State()        # Фамилия
    street = State()           # Улица
    city = State()             # Город
    state = State()            # Штат
    zip_code = State()         # ZIP-код
    dob = State()              # Дата рождения
    annual_income = State()    # Годовой доход
    confirm = State()          # Подтверждение

class SSN(StatesGroup):
    waiting_for_ssn = State()  # Ожидание ввода SSN
