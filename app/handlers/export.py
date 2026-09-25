import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message

from app.repositories.export import ExportReadError
from app.services.export import ExportService


export_router = Router()
logger = logging.getLogger(__name__)


@export_router.message(F.text == "Скачать в Excel")
async def download_excel(
    message: Message, state: FSMContext, export_service: ExportService
) -> None:
    await state.clear()
    try:
        content = await export_service.create_excel()
    except ExportReadError:
        logger.exception("Ошибка выгрузки данных в Excel")
        await message.answer("Не удалось подготовить Excel-файл. Попробуйте позже.")
        return

    date = datetime.now(ZoneInfo("Europe/Moscow")).strftime("%Y-%m-%d_%H-%M")
    document = BufferedInputFile(content, filename=f"warehouse_{date}.xlsx")
    await message.answer_document(document, caption="Данные склада в Excel")
