from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from utils.exel_manager import ExelManager
from states.employy_states import EmployeeState

employy_router = Router()


@employy_router.message(F.text == "Добавить сотрудника")
async def add_employy(message: Message, state: FSMContext):
    text = "Введите Telegram ID сотрудника: "
    await message.answer(text)
    await state.set_state(EmployeeState.telegram_id)


@employy_router.message(EmployeeState.telegram_id)
async def get_employee_telegram_id(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("ID должен быть числом. Попробуйте снова:")
        return

    await state.update_data(telegram_id=message.text)
    await message.answer("Теперь введите имя сотрудника:")
    await state.set_state(EmployeeState.name)


@employy_router.message(EmployeeState.name)
async def get_employee_name(message: Message, state: FSMContext):
    user_data = await state.get_data()
    telegram_id = user_data["telegram_id"]
    name = message.text

    exel_manager = ExelManager()
    exel_manager.add_employee(telegram_id, name)

    await message.answer(f"Сотрудник {name} (ID: {telegram_id}) успешно добавлен ✅")
    await state.clear()
