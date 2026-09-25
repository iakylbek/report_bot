import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import BOT_TOKEN, DATABASE_URL, ADMIN_ID
from app.access import AccessMiddleware
from app.database import create_engine, create_tables
from app.handlers import (
    employee_router,
    entering_data_router,
    export_router,
    operation_router,
    product_router,
    report_router,
    remains_router,
    start_router,
)
from app.repositories.employee import EmployeeRepository
from app.repositories.export import ExportRepository
from app.repositories.operation import OperationRepository
from app.repositories.product import ProductRepository
from app.services.employee import EmployeeService
from app.services.export import ExportService
from app.services.operation import OperationService
from app.services.product import ProductService


async def main() -> None:
    if not DATABASE_URL:
        raise RuntimeError("Укажите DATABASE_URL в .env для подключения к PostgreSQL")

    bot = Bot(token=BOT_TOKEN)
    dispatcher = Dispatcher(
        storage=MemoryStorage(), events_isolation=SimpleEventIsolation()
    )
    dispatcher.message.outer_middleware(AccessMiddleware())
    dispatcher.callback_query.outer_middleware(AccessMiddleware())

    dispatcher.include_routers(
        start_router,
        export_router,
        entering_data_router,
        remains_router,
        report_router,
        employee_router,
        product_router,
        operation_router,
    )

    engine = create_engine(DATABASE_URL)
    try:
        await create_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        employee_service = EmployeeService(EmployeeRepository(sessions))
        if ADMIN_ID:
            await employee_service.ensure_first_user(ADMIN_ID)
        export_service = ExportService(ExportRepository(sessions))
        product_service = ProductService(ProductRepository(sessions))
        operation_service = OperationService(OperationRepository(sessions))
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(
            bot, employee_service=employee_service, product_service=product_service,
            operation_service=operation_service, export_service=export_service,
            close_bot_session=False,
        )
    finally:
        await engine.dispose()
        await bot.session.close()


def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    asyncio.run(main())


if __name__ == "__main__":
    run()
