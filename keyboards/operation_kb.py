from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.exel_manager import ExelManager


def get_product_keyboard():
    exel = ExelManager()
    sheet = exel.workbook["Товары"]
    products = [sheet.cell(row=i, column=2).value for i in range(2, sheet.max_row + 1)]

    keyboard = []
    for p in products:
        if p:
            keyboard.append([
                InlineKeyboardButton(text=p, callback_data=f"product:{p}")
            ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_operation_type_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Поступление", callback_data="type:Поступление")],
            [InlineKeyboardButton(text="Отгрузка", callback_data="type:Отгрузка")],
        ]
    )
