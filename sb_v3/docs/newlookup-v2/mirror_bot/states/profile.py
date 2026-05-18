from aiogram.fsm.state import State, StatesGroup


class ProfileStates(StatesGroup):
    entering_archive_channel_id = State()
