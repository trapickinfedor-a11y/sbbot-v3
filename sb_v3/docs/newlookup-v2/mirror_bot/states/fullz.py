from aiogram.fsm.state import State, StatesGroup


class FullzStates(StatesGroup):
    select_type = State()
    select_state = State()
    select_credit_score = State()
    select_age = State()
    select_gender = State()
    select_carrier_exclusion = State()
    select_bank_exclusion = State()
    select_report_group = State()
    select_quantity = State()
    waiting_custom_qty = State()
    select_company_type = State()
    select_loan_size = State()
    select_fixed_quantity = State()
    waiting_fixed_custom_qty = State()
    fixed_confirmation = State()
    confirmation = State()

