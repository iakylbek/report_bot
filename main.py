import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from handlers import (
    start_router,
    remains_router,
    total_remains_router,
    specific_remains_router,
    receipt_router,
    total_receipt_router,
    specific_receipt_router,
    shipment_router,
    total_shipment_router,
    specific_shipment_router,
    employy_router,
    product_router,
    operation_router,
)
from config import BOT_TOKEN


async def main():
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Подключаем роутер
    dp.include_routers(
        start_router,

        remains_router,
        total_remains_router,
        specific_remains_router,

        receipt_router,
        specific_receipt_router,
        total_receipt_router,

        shipment_router,
        total_shipment_router,
        specific_shipment_router,

        employy_router,
        product_router,
        operation_router,
    )

    # Запускаем бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
