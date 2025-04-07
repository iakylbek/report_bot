from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from keyboards.period_kb import get_period_keyboard
from states_group import ProductShipments

OPERATION = "specific_shipment"
specific_shipment_router = Router()

@specific_shipment_router.callback_query(F.data == "specific_shipment")
async def get_product_name(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название товара:")
    await state.set_state(ProductShipments.product_name_state)
    await callback.answer()

@specific_shipment_router.message(StateFilter(ProductShipments.product_name_state))
async def get_period(message: Message, state: FSMContext):
    await state.update_data(product_name=message.text)
    await message.answer("Выберите период:", reply_markup=get_period_keyboard(OPERATION))
    await state.set_state(ProductShipments.period_state)

# Обрабатываем выбор периода для конкретного товара
@specific_shipment_router.callback_query(
    StateFilter(ProductShipments.period_state), F.data.startswith(f"{OPERATION}_period_")
)
async def show_product_shipment(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    product_name = user_data.get("product_name")
    period = "неделю" if "week" in callback.data else "месяц"

    response_text = f"📦 Отгрузка товара '{product_name}' за {period}: 10 шт."

    await callback.message.answer(response_text)
    await state.clear()
    await callback.answer()
