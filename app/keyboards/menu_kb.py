from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [
                KeyboardButton(text="Остатки"),
                KeyboardButton(text="Отгрузки"),
            ],
            [
                KeyboardButton(text="Поступления"),
                KeyboardButton(text="Внести данные"),
            ],
            [KeyboardButton(text="Скачать в Excel")],
        ],
    )
