from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from states_group import ProductSearch


specific_remains_router = Router()

@specific_remains_router.callback_query(F.data == "specific_remains")
async def get_product_name(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProductSearch.product_name)
    await callback.message.answer("Введите название товара:")


@specific_remains_router.message(StateFilter(ProductSearch.product_name))
async def show_product_info(message: Message, state: FSMContext):
    product_name = message.text

    product_info = (
        f"Информация о товаре '{product_name}':\n🔹 Остаток: 15 шт.\n💰 Цена: 500₽"
    )

    await message.answer(product_info)
    await state.clear()
