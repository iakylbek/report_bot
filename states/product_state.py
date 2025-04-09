from aiogram.fsm.state import State, StatesGroup


class ProductState(StatesGroup):
    article = State()
    name = State()
    price = State()
    responsible = State()
    comment = State()
