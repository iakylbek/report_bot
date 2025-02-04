from aiogram import Router, F
from aiogram.types import Message

echo_router = Router()

@echo_router.message(F.text)
async def echo(message: Message):
    await message.answer(message.text)
