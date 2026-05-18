from aiogram.fsm.state import State, StatesGroup


class AccountStates(StatesGroup):
    waiting_for_quantity = State()
    waiting_custom_qty = State()
    confirm_bulk_purchase = State()
