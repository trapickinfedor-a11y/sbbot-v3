from aiogram.fsm.state import State, StatesGroup


class CCFilterStates(StatesGroup):
    waiting_bin = State()
    waiting_zip = State()
