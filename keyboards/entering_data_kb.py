from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_data_entry_keyboard():
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text="Добавить сотрудника")],
            [KeyboardButton(text="Добавить товар")],
            [KeyboardButton(text="Внести поступления/отгрузку")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
    )
    return keyboard
