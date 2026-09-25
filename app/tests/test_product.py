import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.entering_data import back_to_main_menu
from app.handlers.start import start
from app.handlers.product import (
    start_add_product, get_article, get_name, get_price, get_comment,
    choose_kind, get_responsible,
)
from app.models import Product
from app.repositories.product import ProductRepository
from app.services.product import ProductService
from app.services.employee import EmployeeService
from app.states.product_state import ProductState


def message(text):
    return SimpleNamespace(
        text=text, answer=AsyncMock(), from_user=SimpleNamespace(full_name="Тест")
    )


def callback(data):
    return SimpleNamespace(data=data, answer=AsyncMock(), message=SimpleNamespace(
        edit_text=AsyncMock(), answer=AsyncMock(), edit_reply_markup=AsyncMock(),
    ))


class ProductTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.storage = MemoryStorage()
        self.state = FSMContext(self.storage, StorageKey(bot_id=1, chat_id=1, user_id=1))
        self.session = AsyncMock(spec=AsyncSession)
        self.session.__aenter__.return_value = self.session
        self.service = ProductService(ProductRepository(MagicMock(return_value=self.session)))

    async def asyncTearDown(self):
        await self.storage.close()

    async def fill_product(self):
        await start_add_product(message("Добавить товар"), self.state)
        key = (await self.state.get_data())["catalog_selection"]
        employees = AsyncMock(spec=EmployeeService)
        employees.get_names.return_value = ["Анна"]
        await choose_kind(callback(f"catalog_kind:{key}:component"), self.state, self.service, employees)
        await get_article(message("00123"), self.state)
        await get_name(message("Контроллер"), self.state)
        await get_price(message("125.50"), self.state)
        key = (await self.state.get_data())["catalog_selection"]
        await get_responsible(callback(f"component_responsible:{key}:0"), self.state)

    async def test_complete_dialog_preserves_article_and_price(self):
        await self.fill_product()
        self.assertEqual(await self.state.get_state(), ProductState.comment.state)
        self.session.add.assert_not_called()
        self.session.commit.assert_not_awaited()
        reply = message("-")
        await get_comment(reply, self.state, self.service)
        product = self.session.add.call_args.args[0]
        self.assertIsInstance(product, Product)
        self.assertEqual(product.responsible, "Анна")
        self.assertEqual(product.kind, "component")
        self.assertEqual(
            (product.article, product.name, product.price, product.comment),
            ("00123", "Контроллер", Decimal("125.50"), "-"),
        )
        self.session.commit.assert_awaited_once()
        self.assertIsNone(await self.state.get_state())
        self.assertEqual(await self.state.get_data(), {})
        self.assertIn("успешно добавлено", reply.answer.call_args.args[0])

    async def test_invalid_price_keeps_step(self):
        await self.state.set_state(ProductState.price)
        for value in (None, "", "abc", "-1", "NaN", "Infinity", "1e3", "1.2.3", "²"):
            await get_price(message(value), self.state)
            self.assertEqual(await self.state.get_state(), ProductState.price.state)
            self.assertEqual(await self.state.get_data(), {})

    async def test_invalid_text_keeps_step(self):
        for handler, step in (
            (get_article, ProductState.article), (get_name, ProductState.name),
            (get_comment, ProductState.comment),
        ):
            for value in (None, " ", "\x00"):
                await self.state.set_state(step)
                if handler is get_comment:
                    await handler(message(value), self.state, self.service)
                else:
                    await handler(message(value), self.state)
                self.assertEqual(await self.state.get_state(), step.state)
        self.session.add.assert_not_called()

    async def test_cancellation_at_every_step(self):
        for step in ProductState.__all_states__:
            for handler in (back_to_main_menu, start):
                await self.state.set_state(step)
                await self.state.update_data(article="00123")
                await handler(message("navigation"), self.state)
                self.assertIsNone(await self.state.get_state())
                self.assertEqual(await self.state.get_data(), {})
        self.session.add.assert_not_called()

    async def test_failed_commit_keeps_dialog(self):
        await self.fill_product()
        data = await self.state.get_data()
        self.session.commit.side_effect = SQLAlchemyError("Unavailable")
        reply = message("-")
        with self.assertLogs("app.handlers.product", level="ERROR"):
            await get_comment(reply, self.state, self.service)
        self.assertEqual(await self.state.get_state(), ProductState.comment.state)
        self.assertEqual(await self.state.get_data(), data)
        self.assertNotIn("успешно добавлен", reply.answer.call_args.args[0])
        self.session.__aexit__.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
