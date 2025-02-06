from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_remains_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Общий остаток", callback_data="total_remains"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Определенный товар", callback_data="specific_remains"
                )
            ],
        ],
    )
    return keyboard
