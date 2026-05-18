from aiogram.fsm.state import State, StatesGroup


class OrderStates(StatesGroup):
    waiting_data = State()
    waiting_bulk_data = State()
    confirmation = State()


class TopupStates(StatesGroup):
    waiting_amount = State()
    waiting_payment = State()


class SendMoneyStates(StatesGroup):
    waiting_user_id = State()
    waiting_amount = State()
    confirmation = State()


class CouponStates(StatesGroup):
    waiting_code = State()


class ESIMStates(StatesGroup):
    selecting_type = State()
    selecting_operator = State()
    selecting_period_or_data = State()
    confirmation = State()
    confirm_bulk_purchase = State()


class ESIMConfigStates(StatesGroup):
    selecting_operator = State()
    selecting_state = State()
    selecting_cs = State()
    selecting_report = State()
    selecting_qty = State()
    confirmation = State()


class DocumentStates(StatesGroup):
    waiting_data = State()
    confirmation = State()


class RandomFullzStates(StatesGroup):
    confirmation = State()
