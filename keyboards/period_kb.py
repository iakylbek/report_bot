from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_period_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Неделя", callback_data="period_week")],
            [InlineKeyboardButton(text="📅 Месяц", callback_data="period_month")]
        ]
    )
    return keyboard
