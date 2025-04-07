from aiogram.fsm.state import StatesGroup, State


class ProductSearch(StatesGroup):
    product_name = State()

class ProductReceipts(StatesGroup):
    product_name_state = State()
    period_state = State()

class ProductShipments(StatesGroup):
    product_name_state = State()
    period_state = State()
