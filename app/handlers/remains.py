import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards.menu_kb import get_menu_keyboard
from app.repositories.product import ProductReadError
from app.services.product import ProductService


remains_router = Router()
logger = logging.getLogger(__name__)


@remains_router.message(F.text == "Остатки")
async def show_remains(
    message: Message, state: FSMContext, product_service: ProductService
) -> None:
    await state.clear()
    try:
        products = await product_service.get_remains()
    except ProductReadError:
        logger.exception("Ошибка получения остатков")
        await message.answer(
            "Не удалось загрузить остатки. Попробуйте позже.",
            reply_markup=get_menu_keyboard(),
        )
        return
    if not products:
        await message.answer("Товары ещё не добавлены.", reply_markup=get_menu_keyboard())
        return

    text = "Остатки на складе:\n"
    total = 0
    for product in products:
        quantity = product["quantity"]
        total += quantity
        # Ограничиваем подписи, чтобы одна строка помещалась в сообщение Telegram.
        name = product["name"][:180]
        article = product["article"][:80]
        line = f"\n{name} · {article} (ID {product['id']}): {quantity} шт."
        if quantity < 0:
            line += " ⚠️ Отгрузок больше поступлений"
        if len((text + line).encode("utf-8")) > 3500:
            await message.answer(text, reply_markup=get_menu_keyboard())
            text = "Остатки (продолжение):\n"
        text += line
    summary = f"\n\nВсего по учёту: {total} шт."
    if len((text + summary).encode("utf-8")) > 3500:
        await message.answer(text, reply_markup=get_menu_keyboard())
        text = ""
    await message.answer(text + summary, reply_markup=get_menu_keyboard())
