from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards.menu_kb import get_menu_keyboard


start_router = Router()


@start_router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    user_name = message.from_user.full_name if message.from_user else "пользователь"
    text = (
        f"Здравствуйте, {user_name}!\n"
        "Добро пожаловать в бот для склада"
    )
    await message.answer(text, reply_markup=get_menu_keyboard())
