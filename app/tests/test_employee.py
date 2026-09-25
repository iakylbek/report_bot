import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.employee import (
    add_employee,
    get_employee_name,
    get_employee_telegram_id,
)
from app.models import Employee
from app.repositories.employee import EmployeeReadError, EmployeeRepository
from app.services.employee import EmployeeService
from app.states.employee_state import EmployeeState


def make_message(text: str | None) -> SimpleNamespace:
    return SimpleNamespace(
        text=text,
        from_user=SimpleNamespace(full_name="Тест"),
        answer=AsyncMock(),
    )


class EmployeeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.storage = MemoryStorage()
        self.state = FSMContext(
            storage=self.storage, key=StorageKey(bot_id=1, chat_id=1, user_id=1)
        )
        self.session = AsyncMock(spec=AsyncSession)
        self.session.__aenter__.return_value = self.session
        self.sessions = MagicMock(return_value=self.session)
        self.repository = EmployeeRepository(self.sessions)
        self.service = EmployeeService(self.repository)

    async def asyncTearDown(self) -> None:
        await self.storage.close()

    async def enter_id(self) -> None:
        await add_employee(make_message("Добавить сотрудника"), self.state)
        await get_employee_telegram_id(make_message("1234567"), self.state)

    async def test_complete_dialog(self) -> None:
        await add_employee(make_message("Добавить сотрудника"), self.state)
        self.assertEqual(await self.state.get_state(), EmployeeState.telegram_id.state)
        await get_employee_telegram_id(make_message("1234567"), self.state)
        self.assertEqual(await self.state.get_state(), EmployeeState.name.state)
        self.session.commit.assert_not_awaited()

        message = make_message("Анна O'Neil")
        await get_employee_name(message, self.state, self.service)
        self.session.commit.assert_awaited_once()
        self.session.add.assert_called_once()
        employee = self.session.add.call_args.args[0]
        self.assertIsInstance(employee, Employee)
        self.assertEqual(employee.telegram_id, "1234567")
        self.assertEqual(employee.name, "Анна O'Neil")
        self.assertIsNone(await self.state.get_state())
        self.assertEqual(await self.state.get_data(), {})
        self.assertIn("успешно добавлен", message.answer.call_args.args[0])
        self.assertIn("reply_markup", message.answer.call_args.kwargs)

    async def test_invalid_id_keeps_first_step(self) -> None:
        await add_employee(make_message("Добавить сотрудника"), self.state)
        for value in (None, "", "abc", "0", "000", "-1", "1.2", "²"):
            with self.subTest(value=value):
                await get_employee_telegram_id(make_message(value), self.state)
                self.assertEqual(await self.state.get_state(), EmployeeState.telegram_id.state)
                self.assertEqual(await self.state.get_data(), {})
        self.session.commit.assert_not_awaited()

    async def test_invalid_name_keeps_id(self) -> None:
        await self.enter_id()
        for value in (None, "", "   ", "\x00"):
            with self.subTest(value=value):
                await get_employee_name(make_message(value), self.state, self.service)
                self.assertEqual(await self.state.get_state(), EmployeeState.name.state)
                self.assertEqual(await self.state.get_data(), {"telegram_id": "1234567"})
        self.session.commit.assert_not_awaited()

    async def test_storage_error_does_not_confirm_success(self) -> None:
        await self.enter_id()
        self.session.commit.side_effect = SQLAlchemyError("Database is unavailable")
        message = make_message("Анна")
        with self.assertLogs("app.handlers.employee", level="ERROR"):
            await get_employee_name(message, self.state, self.service)
        self.assertEqual(await self.state.get_state(), EmployeeState.name.state)
        self.assertEqual(await self.state.get_data(), {"telegram_id": "1234567"})
        self.assertNotIn("успешно добавлен", message.answer.call_args.args[0])

    async def test_leading_zeros_reach_orm_unchanged(self) -> None:
        await add_employee(make_message("Добавить сотрудника"), self.state)
        await get_employee_telegram_id(make_message("001234567"), self.state)
        self.assertEqual(await self.state.get_data(), {"telegram_id": "001234567"})
        await get_employee_name(make_message("Анна"), self.state, self.service)
        self.assertEqual(self.session.add.call_args.args[0].telegram_id, "001234567")

    async def test_read_employee_names_error(self) -> None:
        self.session.scalars.side_effect = SQLAlchemyError("Unavailable")
        with self.assertRaises(EmployeeReadError):
            await self.service.get_names()


if __name__ == "__main__":
    unittest.main()
