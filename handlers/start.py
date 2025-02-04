from aiogram import Router, F
from aiogram.types import Message
from keyboards.menu_kb import get_menu_keyboard

start_router = Router()

@start_router.message(F.text == "/start")
async def start(message: Message):
    text = f"Здравстуйте {message.from_user.full_name}!\nДобро пожаловать в бот для склада"
    await message.answer(text, reply_markup=get_menu_keyboard())
