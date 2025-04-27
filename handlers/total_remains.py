from aiogram import types
from aiogram import Router

from utils.exel_manager import ExelManager

total_remains_router = Router()

@total_remains_router.callback_query(lambda c: c.data == 'total_remains')
async def process_total_remain(callback: types.CallbackQuery):
    em = ExelManager()
    all_products = em.get_all_remains()

    # Если товары есть, отправляем их в чат
    if all_products:
        products_info = "\n".join(all_products)
    else:
        products_info = "Нет данных о товарах."

    await callback.message.answer(products_info)
    await callback.answer()
