import logging
from secrets import token_hex

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards.entering_data_kb import get_cancel_keyboard, get_data_entry_keyboard
from app.keyboards.product_kb import get_components_keyboard, get_product_kind_keyboard
from app.keyboards.responsible_kb import get_responsible_keyboard
from app.repositories.employee import EmployeeReadError
from app.repositories.product import ProductReadError, ProductSaveError
from app.services.employee import EmployeeService
from app.services.product import ProductService, parse_price, parse_quantity, validate_text
from app.states.product_state import ProductState


product_router = Router()
logger = logging.getLogger(__name__)


@product_router.message(F.text == "Добавить товар")
async def start_add_product(message: Message, state: FSMContext) -> None:
    await state.clear()
    key = token_hex(4)
    await state.update_data(catalog_selection=key)
    await state.set_state(ProductState.kind)
    await message.answer("Добавление товара", reply_markup=get_cancel_keyboard())
    await message.answer("Что добавить?", reply_markup=get_product_kind_keyboard(key))


async def valid_callback(callback: CallbackQuery, state: FSMContext, step: str) -> bool:
    data = await state.get_data()
    parts = (callback.data or "").split(":")
    valid = (
        await state.get_state() == step and len(parts) == 3
        and parts[1] == data.get("catalog_selection") and callback.message is not None
    )
    if not valid:
        await callback.answer("Этот выбор уже недоступен.")
    return valid


@product_router.callback_query(F.data.startswith("catalog_kind:"))
async def choose_kind(
    callback: CallbackQuery, state: FSMContext, product_service: ProductService,
    employee_service: EmployeeService,
) -> None:
    if not await valid_callback(callback, state, ProductState.kind.state):
        return
    kind = callback.data.split(":")[2]
    if kind not in ("component", "product"):
        await callback.answer("Неизвестный тип товара.")
        return
    try:
        if kind == "component":
            names = await employee_service.get_names()
            if not names:
                await callback.answer("Сначала добавьте сотрудника.", show_alert=True)
                return
            await state.update_data(responsible_names=names)
        else:
            components = await product_service.get_components()
            if not components:
                await callback.answer("Сначала добавьте комплектующие.", show_alert=True)
                return
            await state.update_data(
                choices={str(p.id): f"{p.name} · {p.article} (ID {p.id})" for p in components},
                selected={},
            )
    except (EmployeeReadError, ProductReadError):
        logger.exception("Ошибка загрузки данных для товара")
        await callback.answer("Не удалось загрузить данные. Попробуйте позже.", show_alert=True)
        return
    await state.update_data(kind=kind)
    await state.set_state(ProductState.article)
    await callback.answer()
    await callback.message.edit_text("Введите артикул:")


@product_router.message(ProductState.article)
async def get_article(message: Message, state: FSMContext) -> None:
    try:
        article = validate_text(message.text)
    except ValueError as error:
        await message.answer(str(error))
        return
    await state.update_data(article=article)
    await state.set_state(ProductState.name)
    await message.answer("Введите наименование:")


async def show_components(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    key = token_hex(4)
    await state.update_data(catalog_selection=key)
    await state.set_state(ProductState.components)
    await message.answer(
        f"Состав продукта «{data['name'][:100]}». Выбрано позиций: {len(data['selected'])}.\n"
        "Выберите комплектующее и укажите количество на один продукт.\n"
        "Повторный выбор позволяет изменить количество.",
        reply_markup=get_components_keyboard(data["choices"], data["selected"], key),
    )


@product_router.message(ProductState.name)
async def get_name(message: Message, state: FSMContext) -> None:
    try:
        name = validate_text(message.text)
    except ValueError as error:
        await message.answer(str(error))
        return
    await state.update_data(name=name)
    data = await state.get_data()
    if data["kind"] == "product":
        await show_components(message, state)
    else:
        await state.set_state(ProductState.price)
        await message.answer("Введите цену комплектующего:")


@product_router.message(ProductState.price)
async def get_price(message: Message, state: FSMContext) -> None:
    try:
        price = parse_price(message.text)
    except ValueError as error:
        await message.answer(str(error))
        return
    data = await state.get_data()
    key = token_hex(4)
    await state.update_data(price=str(price), catalog_selection=key)
    await state.set_state(ProductState.responsible)
    await message.answer(
        "Выберите ответственного за комплектующее:",
        reply_markup=get_responsible_keyboard(data["responsible_names"], key),
    )


@product_router.callback_query(F.data.startswith("component_responsible:"))
async def get_responsible(callback: CallbackQuery, state: FSMContext) -> None:
    if not await valid_callback(callback, state, ProductState.responsible.state):
        return
    data = await state.get_data()
    index = callback.data.split(":")[2]
    names = data["responsible_names"]
    if not index.isascii() or not index.isdigit() or len(index) > 9 or int(index) >= len(names):
        await callback.answer("Некорректный сотрудник.")
        return
    await state.update_data(responsible=names[int(index)])
    await state.set_state(ProductState.comment)
    await callback.answer()
    await callback.message.edit_text(f"Ответственный: {names[int(index)]}")
    await callback.message.answer("Введите комментарий (или '-' если нет):")


@product_router.message(ProductState.comment)
async def get_comment(message: Message, state: FSMContext, product_service: ProductService) -> None:
    try:
        comment = validate_text(message.text)
    except ValueError as error:
        await message.answer(str(error))
        return
    data = await state.get_data()
    try:
        await product_service.add_component(
            article=data["article"], name=data["name"], price=data["price"],
            comment=comment, responsible=data["responsible"],
        )
    except ValueError as error:
        await message.answer(str(error))
        return
    except ProductSaveError:
        logger.exception("Ошибка сохранения комплектующего")
        await message.answer("Не удалось сохранить комплектующее. Повторите комментарий позже или нажмите «⬅️ Назад».")
        return
    await state.clear()
    await message.answer("✅ Комплектующее успешно добавлено!", reply_markup=get_data_entry_keyboard())


@product_router.callback_query(F.data.startswith("catalog_component:"))
async def choose_component(callback: CallbackQuery, state: FSMContext) -> None:
    if not await valid_callback(callback, state, ProductState.components.state):
        return
    data = await state.get_data()
    component_id = callback.data.split(":")[2]
    if component_id not in data["choices"]:
        await callback.answer("Неизвестное комплектующее.")
        return
    await state.update_data(component_id=component_id)
    await state.set_state(ProductState.component_quantity)
    await callback.answer()
    await callback.message.edit_text(
        f"{data['choices'][component_id][:150]}\nВведите количество на один продукт:"
    )


@product_router.message(ProductState.component_quantity)
async def get_component_quantity(message: Message, state: FSMContext) -> None:
    try:
        quantity = parse_quantity(message.text)
    except ValueError as error:
        await message.answer(str(error))
        return
    data = await state.get_data()
    selected = data["selected"]
    selected[data["component_id"]] = quantity
    await state.update_data(selected=selected)
    await show_components(message, state)


@product_router.callback_query(F.data.startswith("catalog_page:"))
async def component_page(callback: CallbackQuery, state: FSMContext) -> None:
    if not await valid_callback(callback, state, ProductState.components.state):
        return
    data = await state.get_data()
    page = callback.data.split(":")[2]
    if not page.isascii() or not page.isdigit() or len(page) > 9 or int(page) * 10 >= len(data["choices"]):
        await callback.answer("Некорректная страница.")
        return
    await callback.answer()
    key = token_hex(4)
    await state.update_data(catalog_selection=key)
    await callback.message.edit_reply_markup(reply_markup=get_components_keyboard(
        data["choices"], data["selected"], key, int(page),
    ))


@product_router.callback_query(F.data.startswith("catalog_save:"))
async def save_product(callback: CallbackQuery, state: FSMContext, product_service: ProductService) -> None:
    if not await valid_callback(callback, state, ProductState.components.state):
        return
    data = await state.get_data()
    try:
        await product_service.add_product(
            data["article"], data["name"], {int(key): value for key, value in data["selected"].items()},
        )
    except ValueError as error:
        await callback.answer(str(error), show_alert=True)
        return
    except ProductSaveError:
        logger.exception("Ошибка сохранения продукта")
        await callback.answer("Не удалось сохранить продукт. Попробуйте позже.", show_alert=True)
        return
    await state.clear()
    await callback.answer()
    await callback.message.edit_text("✅ Продукт и его состав сохранены!")
    await callback.message.answer("Внести данные:", reply_markup=get_data_entry_keyboard())


@product_router.message(ProductState.kind)
@product_router.message(ProductState.responsible)
@product_router.message(ProductState.components)
async def ask_selection(message: Message) -> None:
    await message.answer("Выберите вариант кнопкой под сообщением.")
