import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards.entering_data_kb import get_cancel_keyboard, get_data_entry_keyboard
from app.repositories.employee import EmployeeSaveError
from app.services.employee import EmployeeService, parse_telegram_id, validate_name
from app.states.employee_state import EmployeeState


employee_router = Router()
logger = logging.getLogger(__name__)


@employee_router.message(F.text == "Добавить сотрудника")
async def add_employee(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(EmployeeState.telegram_id)
    await message.answer(
        "Введите Telegram ID сотрудника:", reply_markup=get_cancel_keyboard()
    )


@employee_router.message(EmployeeState.telegram_id)
async def get_employee_telegram_id(message: Message, state: FSMContext) -> None:
    try:
        telegram_id = parse_telegram_id(message.text)
    except ValueError as error:
        await message.answer(str(error))
        return

    await state.update_data(telegram_id=telegram_id)
    await state.set_state(EmployeeState.name)
    await message.answer("Теперь введите имя сотрудника:")


@employee_router.message(EmployeeState.name)
async def get_employee_name(
    message: Message, state: FSMContext, employee_service: EmployeeService
) -> None:
    try:
        name = validate_name(message.text)
    except ValueError as error:
        await message.answer(str(error))
        return

    user_data = await state.get_data()
    telegram_id = user_data["telegram_id"]
    try:
        await employee_service.add_employee(telegram_id, name)
    except EmployeeSaveError:
        logger.exception("Ошибка сохранения сотрудника")
        await message.answer(
            "Не удалось подтвердить сохранение сотрудника. "
            "Попробуйте позже или нажмите «⬅️ Назад»."
        )
        return

    await state.clear()
    await message.answer(
        f"Сотрудник {name} (ID: {telegram_id}) успешно добавлен ✅",
        reply_markup=get_data_entry_keyboard(),
    )
