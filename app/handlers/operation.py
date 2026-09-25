import logging
from secrets import token_hex

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards.entering_data_kb import get_cancel_keyboard, get_data_entry_keyboard
from app.keyboards.operation_kb import get_operation_type_keyboard, get_product_keyboard
from app.repositories.operation import OperationSaveError
from app.repositories.product import ProductReadError
from app.services.operation import OperationService, parse_quantity
from app.services.product import ProductService, validate_text
from app.states.operation_state import OperationState


operation_router = Router()
logger = logging.getLogger(__name__)


@operation_router.message(F.text == "Внести поступления/отгрузку")
async def start_add_operation(
    message: Message, state: FSMContext, product_service: ProductService
) -> None:
    await state.clear()
    try:
        products = await product_service.get_products()
    except ProductReadError:
        logger.exception("Ошибка загрузки товаров")
        await message.answer("Не удалось загрузить товары. Попробуйте позже.")
        return
    if not products:
        await message.answer("Список товаров пуст. Сначала добавьте товар.")
        return

    selection = token_hex(4)
    choices = {str(p.id): f"{p.name} · {p.article} (ID {p.id})" for p in products}
    await state.update_data(products=choices, operation_selection=selection)
    await state.set_state(OperationState.product)
    await message.answer("Внесение операции", reply_markup=get_cancel_keyboard())
    await message.answer("Выберите товар:", reply_markup=get_product_keyboard(choices, selection))


@operation_router.callback_query(F.data.startswith("op_product:"))
async def product_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    parts = (callback.data or "").split(":")
    choices = data.get("products", {})
    if (
        await state.get_state() != OperationState.product.state or len(parts) != 3
        or parts[1] != data.get("operation_selection") or parts[2] not in choices
        or callback.message is None
    ):
        await callback.answer("Этот выбор уже недоступен.")
        return
    await state.update_data(product_id=int(parts[2]))
    await state.set_state(OperationState.op_type)
    await callback.answer()
    await callback.message.edit_text(
        f"Товар: {choices[parts[2]]}\nТеперь выберите тип операции:",
        reply_markup=get_operation_type_keyboard(parts[1]),
    )


@operation_router.callback_query(F.data.startswith("op_type:"))
async def type_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    parts = (callback.data or "").split(":")
    types = {"receipt": "Поступление", "shipment": "Отгрузка"}
    if (
        await state.get_state() != OperationState.op_type.state or len(parts) != 3
        or parts[1] != data.get("operation_selection") or parts[2] not in types
        or callback.message is None
    ):
        await callback.answer("Этот выбор уже недоступен.")
        return
    op_type = types[parts[2]]
    await state.update_data(op_type=op_type)
    await state.set_state(OperationState.quantity)
    await callback.answer()
    await callback.message.edit_text(f"Тип операции: {op_type}\nТеперь введите количество:")


@operation_router.message(OperationState.product)
@operation_router.message(OperationState.op_type)
async def ask_selection(message: Message) -> None:
    await message.answer("Выберите вариант кнопкой под сообщением.")


@operation_router.message(OperationState.quantity)
async def get_quantity(
    message: Message, state: FSMContext
) -> None:
    try:
        quantity = parse_quantity(message.text)
    except ValueError as error:
        await message.answer(str(error))
        return
    await state.update_data(quantity=quantity)
    await state.set_state(OperationState.comment)
    await message.answer(
        "Введите комментарий (или '-' если его нет):",
        reply_markup=get_cancel_keyboard(),
    )


@operation_router.message(OperationState.comment)
async def get_comment(
    message: Message, state: FSMContext, operation_service: OperationService
) -> None:
    try:
        comment = validate_text(message.text)
    except ValueError as error:
        await message.answer(str(error))
        return
    data = await state.get_data()
    try:
        await operation_service.add_operation(
            data["product_id"], data["op_type"], data["quantity"], comment,
        )
    except ValueError as error:
        await message.answer(str(error))
        return
    except OperationSaveError:
        logger.exception("Ошибка сохранения операции")
        await message.answer(
            "Не удалось подтвердить сохранение операции. Попробуйте позже или нажмите «⬅️ Назад»."
        )
        return
    await state.clear()
    await message.answer("✅ Операция успешно добавлена!", reply_markup=get_data_entry_keyboard())
