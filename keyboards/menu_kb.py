from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [
                KeyboardButton(text="Остатки"),
                KeyboardButton(text="Отгрузки")],
            [
                KeyboardButton(text="Поступления"),
                KeyboardButton(text="Внести данные"),
            ],
        ],
    )
    return keyboard
