from aiogram.fsm.state import State, StatesGroup


class BankStates(StatesGroup):
    waiting_for_quantity = State()
    waiting_custom_qty = State()
    confirm_bulk_purchase = State()
    waiting_name_input = State()
    confirm_on_name = State()
    waiting_brute_search_query = State()
