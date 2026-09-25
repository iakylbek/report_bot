from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.models import Product


TITLES = {"receipt": "Поступления", "ship": "Отгрузки"}


# Префиксы сохранены: кнопки из старых сообщений продолжают работать.
class ReceiptPage(CallbackData, prefix="receipt"):
    product_id: int = 0
    page: int = 0
    period: str = "month"


class ShipmentPage(CallbackData, prefix="ship"):
    product_id: int = 0
    page: int = 0
    period: str = "month"


class ReceiptPeriod(CallbackData, prefix="receipt_period"):
    product_id: int = 0


class ShipmentPeriod(CallbackData, prefix="ship_period"):
    product_id: int = 0


class ReceiptProductsPage(CallbackData, prefix="receipt_products"):
    page: int = 0


class ShipmentProductsPage(CallbackData, prefix="ship_products"):
    page: int = 0


def button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def get_report_keyboard(kind: str) -> InlineKeyboardMarkup:
    operation = "Поступление" if kind == "receipt" else "Отгрузка"
    return InlineKeyboardMarkup(inline_keyboard=[
        [button(f"📦 {operation} всех товаров", f"{kind}_period:0")],
        [button(f"🔍 {operation} определенного товара", f"{kind}_products:0")],
    ])


def get_period_keyboard(kind: str, product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [button("За неделю (7 дней)", f"{kind}:{product_id}:0:week")],
        [button("За месяц (30 дней)", f"{kind}:{product_id}:0:month")],
        [button("Назад", f"{kind}_menu")],
    ])


def get_page_keyboard(kind: str, product_id: int, page: int, has_next: bool, period: str) -> InlineKeyboardMarkup:
    navigation = []
    if page > 0:
        navigation.append(button("⬅️ Предыдущие", f"{kind}:{product_id}:{page - 1}:{period}"))
    if has_next:
        navigation.append(button("Следующие ➡️", f"{kind}:{product_id}:{page + 1}:{period}"))
    rows = [navigation] if navigation else []
    rows.append([button("Выбрать период", f"{kind}_period:{product_id}")])
    if product_id:
        rows.append([button("Выбрать товар", f"{kind}_products:0")])
    rows.append([button(f"К разделу «{TITLES[kind]}»", f"{kind}_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_products_keyboard(kind: str, products: list[Product], page: int, has_next: bool) -> InlineKeyboardMarkup:
    rows = [[button(f"{p.name[:60]} · {p.article[:30]} (ID {p.id})", f"{kind}_period:{p.id}")] for p in products]
    navigation = []
    if page > 0:
        navigation.append(button("⬅️ Предыдущие", f"{kind}_products:{page - 1}"))
    if has_next:
        navigation.append(button("Следующие ➡️", f"{kind}_products:{page + 1}"))
    if navigation:
        rows.append(navigation)
    rows.append([button(f"К разделу «{TITLES[kind]}»", f"{kind}_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
