from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_shipment_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📦 Отгрузка всех товаров", 
                    callback_data="total_shipments"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔍 Отгрузка определенного товара",
                    callback_data="specific_shipment",
                )
            ],
        ]
    )
    return keyboard
