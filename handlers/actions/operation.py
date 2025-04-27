from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states.operation_state import OperationState
from keyboards.operation_kb import get_product_keyboard, get_operation_type_keyboard
from utils.exel_manager import ExelManager

operation_router = Router()


@operation_router.message(F.text == "Внести поступления/отгрузку")
async def start_add_operation(message: Message, state: FSMContext):
    await message.answer("Выберите товар:", reply_markup=get_product_keyboard())
    await state.set_state(OperationState.product)


@operation_router.callback_query(F.data.startswith("product:"))
async def product_chosen(callback: CallbackQuery, state: FSMContext):
    product = callback.data.split("product:")[1]
    await state.update_data(product=product)
    await callback.message.edit_text(f"Товар: {product}\nТеперь выберите тип операции:", reply_markup=get_operation_type_keyboard())
    await state.set_state(OperationState.op_type)
    await callback.answer()


@operation_router.callback_query(F.data.startswith("type:"))
async def type_chosen(callback: CallbackQuery, state: FSMContext):
    op_type = callback.data.split("type:")[1]
    await state.update_data(op_type=op_type)
    await callback.message.edit_text(f"Тип операции: {op_type}\nТеперь введите количество:")
    await state.set_state(OperationState.quantity)
    await callback.answer()


@operation_router.message(OperationState.quantity)
async def get_quantity(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Количество должно быть числом. Попробуйте снова.")
        return

    await state.update_data(quantity=int(message.text))
    await message.answer("Введите комментарий (или '-' если его нет):")
    await state.set_state(OperationState.comment)


@operation_router.message(OperationState.comment)
async def get_comment(message: Message, state: FSMContext):
    data = await state.get_data()

    exel = ExelManager()
    exel.add_operation(
        product_name=data["product"],
        op_type=data["op_type"],
        quantity=data["quantity"],
        comment=message.text,
    )

    await message.answer("✅ Операция успешно добавлена!")
    await state.clear()
