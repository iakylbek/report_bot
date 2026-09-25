from aiogram.fsm.state import State, StatesGroup


class EmployeeState(StatesGroup):
    telegram_id = State()
    name = State()
