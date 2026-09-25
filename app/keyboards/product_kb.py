from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_product_kind_keyboard(key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить комплектующее", callback_data=f"catalog_kind:{key}:component")],
        [InlineKeyboardButton(text="Добавить продукт", callback_data=f"catalog_kind:{key}:product")],
    ])


def get_components_keyboard(
    choices: dict[str, str], selected: dict[str, int], key: str, page: int = 0,
) -> InlineKeyboardMarkup:
    items = list(choices.items())
    rows = []
    for component_id, name in items[page * 10:(page + 1) * 10]:
        prefix = f"✓ {selected[component_id]} шт. · " if component_id in selected else ""
        rows.append([InlineKeyboardButton(
            text=prefix + name[:70], callback_data=f"catalog_component:{key}:{component_id}",
        )])
    navigation = []
    if page:
        navigation.append(InlineKeyboardButton(text="←", callback_data=f"catalog_page:{key}:{page - 1}"))
    if (page + 1) * 10 < len(items):
        navigation.append(InlineKeyboardButton(text="→", callback_data=f"catalog_page:{key}:{page + 1}"))
    if navigation:
        rows.append(navigation)
    rows.append([InlineKeyboardButton(text="Сохранить продукт", callback_data=f"catalog_save:{key}:done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
