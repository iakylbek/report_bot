from aiogram import Router, F
from aiogram.types import Message
from keyboards.remains_kb import get_remains_keyboard

remains_router = Router()

@remains_router.message(F.text == "Остатки")
async def start(message: Message):
    text = "Выберите дейстиве:"
    await message.answer(text, reply_markup=get_remains_keyboard())
