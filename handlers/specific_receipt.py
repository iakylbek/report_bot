from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from keyboards.period_kb import get_period_keyboard
from states_group import ProductReceipts

OPERATION = "specific_receipt"
specific_receipt_router = Router()

@specific_receipt_router.callback_query(F.data == "specific_receipt")
async def get_product_name(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название товара:")
    await state.set_state(ProductReceipts.product_name_state)
    await callback.answer()


@specific_receipt_router.message(StateFilter(ProductReceipts.product_name_state))
async def get_period(message: Message, state: FSMContext):
    await state.update_data(product_name=message.text)  # Сохраняем товар
    await message.answer("Выберите период:", reply_markup=get_period_keyboard(OPERATION))
    await state.set_state(ProductReceipts.period_state)


# Обрабатываем выбор периода для конкретного товара
@specific_receipt_router.callback_query(
    StateFilter(ProductReceipts.period_state), F.data.startswith(f"{OPERATION}_period_")
)
async def show_product_receipts(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    product_name = user_data.get("product_name")
    period = "неделю" if "week" in callback.data else "месяц"

    response_text = f"📦 Поступления товара '{product_name}' за {period}: 10 шт."

    await callback.message.answer(response_text)
    await state.clear()  # Очищаем состояние
    await callback.answer()
