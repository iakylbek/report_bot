import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram import Bot, Dispatcher, Router
from aiogram.types import CallbackQuery, Chat, Message, Update, User
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.access import AccessMiddleware
from app.models import Base, Employee
from app.repositories.employee import EmployeeRepository, EmployeeReadError
from app.services.employee import EmployeeService


class AccessTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.scalar.side_effect = self.db.scalar
        session.commit.side_effect = self.db.commit

        def add(employee):
            employee.id = 1
            self.db.add(employee)

        session.add = MagicMock(side_effect=add)
        self.service = EmployeeService(EmployeeRepository(MagicMock(return_value=session)))

    async def asyncTearDown(self):
        self.db.close()
        self.engine.dispose()

    async def test_bootstrap_once_and_leading_zeros(self):
        await self.service.ensure_first_user("00123")
        self.assertTrue(await self.service.has_access("123"))
        self.assertFalse(await self.service.has_access("456"))
        self.db.get(Employee, 1).name = "Анна"
        self.db.commit()
        await self.service.ensure_first_user("123")
        rows = list(self.db.scalars(select(Employee)))
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0].telegram_id, rows[0].name), ("00123", "Анна"))
        self.db.delete(rows[0])
        self.db.commit()
        self.assertFalse(await self.service.has_access("123"))

    async def test_invalid_bootstrap_id(self):
        for value in ("", "0", "-1", "username"):
            with self.assertRaises(ValueError):
                await self.service.ensure_first_user(value)
        self.assertEqual(list(self.db.scalars(select(Employee))), [])

    async def test_dispatcher_protects_messages_and_callbacks(self):
        bot = Bot(token="123456:LOCAL_TEST_TOKEN")
        dispatcher = Dispatcher()
        dispatcher.message.outer_middleware(AccessMiddleware())
        dispatcher.callback_query.outer_middleware(AccessMiddleware())
        router = Router()
        reached = []

        @router.message()
        async def handle_message(message: Message):
            reached.append("message")

        @router.callback_query()
        async def handle_callback(callback: CallbackQuery):
            reached.append("callback")

        dispatcher.include_router(router)
        service = AsyncMock(spec=EmployeeService)
        user = User(id=123, is_bot=False, first_name="Тест")
        try:
            with patch.object(Message, "answer", new_callable=AsyncMock) as answer, \
                 patch.object(CallbackQuery, "answer", new_callable=AsyncMock) as ack:
                for allowed, chat_type, failure in (
                    (False, "private", False), (True, "private", False),
                    (True, "group", False), (False, "private", True),
                ):
                    for is_callback in (False, True):
                        reached.clear()
                        service.has_access.return_value = allowed
                        service.has_access.side_effect = EmployeeReadError() if failure else None
                        message = Message(message_id=1, date=datetime.now(timezone.utc),
                                          chat=Chat(id=123, type=chat_type), from_user=user, text="/start")
                        callback = CallbackQuery(id="1", from_user=user, chat_instance="1",
                                                 message=message, data="catalog_save:old:done")
                        update = Update(update_id=1, **({"callback_query": callback} if is_callback else {"message": message}))
                        if failure:
                            with self.assertLogs("app.access", level="ERROR"):
                                await dispatcher.feed_update(bot, update, employee_service=service)
                        else:
                            await dispatcher.feed_update(bot, update, employee_service=service)
                        self.assertEqual(bool(reached), allowed and chat_type == "private" and not failure)
                        service.has_access.assert_awaited_with("123")
                        if not reached:
                            if is_callback:
                                self.assertTrue(ack.call_args.kwargs["show_alert"])
                            else:
                                self.assertTrue(answer.call_args.args[0])
        finally:
            await dispatcher.storage.close()
            await bot.session.close()
