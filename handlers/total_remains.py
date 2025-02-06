from aiogram import types
from aiogram import Router

total_remains_router = Router()

@total_remains_router.callback_query(lambda c: c.data == 'total_remains')
async def process_total_remain(callback_query: types.CallbackQuery):
    total_remain_info = "Общий остаток: 1000 единиц на сумму 50000 рублей."
    await callback_query.message.answer(total_remain_info)
    await callback_query.answer()
