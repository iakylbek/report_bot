import logging
from datetime import timezone
from zoneinfo import ZoneInfo

from aiogram.exceptions import TelegramBadRequest
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.keyboards.report_kb import (
    TITLES, ReceiptPage, ReceiptPeriod, ReceiptProductsPage,
    ShipmentPage, ShipmentPeriod, ShipmentProductsPage,
    get_report_keyboard, get_period_keyboard, get_page_keyboard, get_products_keyboard,
)
from app.repositories.operation import OperationReadError
from app.repositories.product import ProductReadError
from app.services.operation import OperationService
from app.services.product import ProductService


MOSCOW = ZoneInfo("Europe/Moscow")
report_router = Router()
logger = logging.getLogger(__name__)


def report_kind(callback: CallbackQuery) -> str:
    return "receipt" if callback.data.startswith("receipt") else "ship"


def menu_text(kind: str) -> str:
    return "Выберите вариант поступлений:" if kind == "receipt" else "Выберите вариант отгрузок:"


def short_text(value: str, limit: int) -> str:
    text = " ".join(value.split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


def format_operations(
    rows: list[dict], page: int, product_id: int, title: str, empty_text: str
) -> str:
    heading = f"{title} всех товаров" if not product_id else f"{title} товара ID {product_id}"
    parts = [f"{heading} · страница {page + 1}"]
    if not rows:
        parts.append("На этой странице записей нет." if page else empty_text)
    for row in rows:
        date = row["created_at"]
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        date = date.astimezone(MOSCOW)
        parts.append(
            f"{short_text(row['name'], 50)} - {short_text(row['article'], 25)}\n"
            f"{date:%d.%m.%Y %H:%M} · {row['quantity']} шт. · {short_text(row['comment'], 40)}"
        )
    return "\n\n".join(parts)


async def edit_page(callback: CallbackQuery, text: str, keyboard: InlineKeyboardMarkup) -> None:
    if not isinstance(callback.message, Message):
        return
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode=None)
    except TelegramBadRequest as error:
        if "message is not modified" not in error.message.lower():
            raise


@report_router.message(F.text.in_(TITLES.values()))
async def show_menu(message: Message, state: FSMContext) -> None:
    kind = "receipt" if message.text == "Поступления" else "ship"
    await state.clear()
    await message.answer(menu_text(kind), reply_markup=get_report_keyboard(kind))


@report_router.callback_query(F.data.in_({"receipt_menu", "ship_menu"}))
async def back_to_menu(callback: CallbackQuery, state: FSMContext) -> None:
    kind = report_kind(callback)
    await state.clear()
    await callback.answer()
    await edit_page(callback, menu_text(kind), get_report_keyboard(kind))


@report_router.callback_query(ReceiptPage.filter())
@report_router.callback_query(ShipmentPage.filter())
async def show_report(
    callback: CallbackQuery, callback_data: ReceiptPage | ShipmentPage,
    state: FSMContext, operation_service: OperationService,
) -> None:
    kind = report_kind(callback)
    operation = "Поступление" if kind == "receipt" else "Отгрузка"
    try:
        rows, has_next = await operation_service.get_page(
            operation, callback_data.page, callback_data.product_id or None, callback_data.period,
        )
    except ValueError as error:
        await callback.answer(str(error), show_alert=True)
        return
    except OperationReadError:
        logger.exception("Ошибка загрузки операций")
        await callback.answer("Не удалось загрузить операции. Попробуйте позже.", show_alert=True)
        return
    await state.clear()
    await callback.answer()
    empty = "Поступлений пока нет." if kind == "receipt" else "Отгрузок пока нет."
    text = format_operations(rows, callback_data.page, callback_data.product_id, TITLES[kind], empty)
    days = 7 if callback_data.period == "week" else 30
    await edit_page(
        callback, text + f"\n\nПериод: последние {days} дней",
        get_page_keyboard(kind, callback_data.product_id, callback_data.page, has_next, callback_data.period),
    )


@report_router.callback_query(ReceiptProductsPage.filter())
@report_router.callback_query(ShipmentProductsPage.filter())
async def choose_product(
    callback: CallbackQuery, callback_data: ReceiptProductsPage | ShipmentProductsPage,
    state: FSMContext, product_service: ProductService,
) -> None:
    try:
        products, has_next = await product_service.get_products_page(callback_data.page)
    except ValueError as error:
        await callback.answer(str(error), show_alert=True)
        return
    except ProductReadError:
        logger.exception("Ошибка загрузки товаров")
        await callback.answer("Не удалось загрузить товары. Попробуйте позже.", show_alert=True)
        return
    await state.clear()
    await callback.answer()
    text = f"Выберите товар · страница {callback_data.page + 1}:"
    if not products:
        text = "На этой странице товаров нет." if callback_data.page else "Товары ещё не добавлены."
    await edit_page(callback, text, get_products_keyboard(report_kind(callback), products, callback_data.page, has_next))


@report_router.callback_query(ReceiptPeriod.filter())
@report_router.callback_query(ShipmentPeriod.filter())
async def choose_period(
    callback: CallbackQuery, callback_data: ReceiptPeriod | ShipmentPeriod, state: FSMContext,
) -> None:
    if not 0 <= callback_data.product_id <= 2**63 - 1:
        await callback.answer("Некорректный товар.", show_alert=True)
        return
    await state.clear()
    await callback.answer()
    await edit_page(callback, "Выберите период:", get_period_keyboard(report_kind(callback), callback_data.product_id))
