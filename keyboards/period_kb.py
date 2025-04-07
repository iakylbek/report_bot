from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_period_keyboard(operation: str):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Неделя", callback_data=f"{operation}_period_week")],
            [InlineKeyboardButton(text="📅 Месяц", callback_data=f"{operation}_period_month")]
        ]
    )
    return keyboard
