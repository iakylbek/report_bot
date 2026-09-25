from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_product_keyboard(products: dict[str, str], selection: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data=f"op_product:{selection}:{product_id}")]
        for product_id, label in products.items()
    ])


def get_operation_type_keyboard(selection: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Поступление", callback_data=f"op_type:{selection}:receipt")],
        [InlineKeyboardButton(text="Отгрузка", callback_data=f"op_type:{selection}:shipment")],
    ])
