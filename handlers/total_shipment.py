from aiogram import Router, F, types
from keyboards.period_kb import get_period_keyboard

OPERATION = "total_shipments"
total_shipment_router = Router()


@total_shipment_router.callback_query(F.data == "total_shipments")
async def process_total_shipment(callback: types.CallbackQuery):
    await callback.message.answer(
        "Выберите период:", reply_markup=get_period_keyboard(OPERATION)
    )
    await callback.answer()


@total_shipment_router.callback_query(F.data.startswith(f"{OPERATION}_period_"))
async def show_all_shipments(callback: types.CallbackQuery):
    period = "неделю" if "week" in callback.data else "месяц"

    response_text = f"📦 Отгрузка всех товаров за {period}: 200 шт."

    await callback.message.answer(response_text)
    await callback.answer()
