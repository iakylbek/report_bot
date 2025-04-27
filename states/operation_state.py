from aiogram.fsm.state import State, StatesGroup


class OperationState(StatesGroup):
    product = State()
    op_type = State()
    quantity = State()
    comment = State()
