from aiogram import Router, F
from aiogram.types import Message
from keyboards.menu_kb import get_menu_keyboard
from keyboards.entering_data_kb import get_data_entry_keyboard

start_router = Router()


@start_router.message(F.text == "/start")
async def start(message: Message):
    text = f"Здравстуйте {message.from_user.full_name}!\nДобро пожаловать в бот для склада"
    await message.answer(text, reply_markup=get_menu_keyboard())


@start_router.message(F.text == "Внести данные")
async def show_data_entry_menu(message: Message):
    await message.answer("Выберите, что хотите внести:", reply_markup=get_data_entry_keyboard())


@start_router.message(F.text == "⬅️ Назад")
async def back_to_main_menu(message: Message):
    await message.answer("Главное меню:", reply_markup=get_menu_keyboard())
