from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states.product_state import ProductState
from utils.exel_manager import ExelManager

product_router = Router()

@product_router.message(F.text == "Добавить товар")
async def start_add_product(message: Message, state: FSMContext):
    await message.answer("Введите артикул товара:")
    await state.set_state(ProductState.article)

@product_router.message(ProductState.article)
async def get_article(message: Message, state: FSMContext):
    await state.update_data(article=message.text)
    await message.answer("Введите наименование товара:")
    await state.set_state(ProductState.name)

@product_router.message(ProductState.name)
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите цену товара:")
    await state.set_state(ProductState.price)

@product_router.message(ProductState.price)
async def get_price(message: Message, state: FSMContext):
    if not message.text.replace(".", "", 1).isdigit():
        await message.answer("Цена должна быть числом. Попробуйте снова:")
        return

    await state.update_data(price=message.text)
    await message.answer("Введите имя ответственного:")
    await state.set_state(ProductState.responsible)

@product_router.message(ProductState.responsible)
async def get_responsible(message: Message, state: FSMContext):
    await state.update_data(responsible=message.text)
    await message.answer("Введите комментарий к товару (или '-' если нет):")
    await state.set_state(ProductState.comment)

@product_router.message(ProductState.comment)
async def get_comment(message: Message, state: FSMContext):
    data = await state.get_data()

    exel = ExelManager()
    exel.add_product(
        article=data["article"],
        name=data["name"],
        price=data["price"],
        responsible=data["responsible"],
        comment=message.text
    )

    await message.answer("✅ Товар успешно добавлен!")
    await state.clear()
