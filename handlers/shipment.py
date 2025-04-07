from aiogram import Router, F
from aiogram.types import Message
from keyboards.shipment_kb import get_shipment_keyboard

shipment_router = Router()

@shipment_router.message(F.text == "Отгрузки")
async def start(message: Message):
    text = "Выберите дейстиве:"
    await message.answer(text, reply_markup=get_shipment_keyboard())
