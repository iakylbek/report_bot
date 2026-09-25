from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards.entering_data_kb import get_data_entry_keyboard
from app.keyboards.menu_kb import get_menu_keyboard


entering_data_router = Router()


@entering_data_router.message(F.text == "Внести данные")
async def show_data_entry_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Выберите, что хотите внести:", reply_markup=get_data_entry_keyboard()
    )


@entering_data_router.message(F.text == "⬅️ Назад")
async def back_to_main_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Главное меню:", reply_markup=get_menu_keyboard())
