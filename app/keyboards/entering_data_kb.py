from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_data_entry_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text="Добавить сотрудника")],
            [KeyboardButton(text="Добавить товар")],
            [KeyboardButton(text="Внести поступления/отгрузку")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
    )


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[[KeyboardButton(text="⬅️ Назад")]],
    )
