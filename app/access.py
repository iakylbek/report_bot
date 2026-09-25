import logging

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from app.repositories.employee import EmployeeReadError


logger = logging.getLogger(__name__)


class AccessMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message | CallbackQuery, data: dict):
        user = event.from_user
        if user is None:
            return
        try:
            allowed = await data["employee_service"].has_access(str(user.id))
        except EmployeeReadError:
            logger.exception("Ошибка проверки доступа")
            text = "Не удалось проверить доступ. Попробуйте позже."
        else:
            text = "Доступ только для сотрудников склада. Обратитесь к сотруднику, имеющему доступ."
            if allowed:
                # Складские данные не должны отправляться в общий чат.
                message = event.message if isinstance(event, CallbackQuery) else event
                if message is not None and message.chat.type == "private":
                    return await handler(event, data)
                text = "Откройте личный чат с ботом."
        if isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=True)
        else:
            await event.answer(text)
