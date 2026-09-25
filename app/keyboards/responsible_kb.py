from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_responsible_keyboard(names: list[str], selection_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=name, callback_data=f"component_responsible:{selection_key}:{index}"
            )]
            for index, name in enumerate(names)
        ],
    )
