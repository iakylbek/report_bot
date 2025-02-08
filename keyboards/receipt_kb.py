from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_receipt_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📦 Поступления всех товаров", 
                    callback_data="total_receipts"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔍 Поступления определенного товара",
                    callback_data="specific_receipt",
                )
            ],
        ]
    )
    return keyboard
