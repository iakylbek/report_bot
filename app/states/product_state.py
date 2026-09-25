from aiogram.fsm.state import State, StatesGroup


class ProductState(StatesGroup):
    kind = State()
    article = State()
    name = State()
    price = State()
    responsible = State()
    comment = State()
    components = State()
    component_quantity = State()
