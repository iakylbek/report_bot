from aiogram import Router, F
from aiogram.types import Message
from keyboards.receipt_kb import get_receipt_keyboard

receipt_router = Router()

@receipt_router.message(F.text == "Поступления")
async def start(message: Message):
    text = "Выберите дейстиве:"
    await message.answer(text, reply_markup=get_receipt_keyboard())
