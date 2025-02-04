import asyncio
from aiogram import Bot, Dispatcher
from handlers import echo_router, start_router
from config import BOT_TOKEN


async def main():
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Подключаем роутер
    dp.include_routers(start_router, echo_router)

    # Запускаем бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
