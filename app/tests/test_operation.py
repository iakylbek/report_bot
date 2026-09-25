import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers import operation as handlers
from app.models import Operation, Product
from app.repositories.operation import OperationRepository
from app.repositories.product import ProductReadError
from app.services.operation import OperationService
from app.services.product import ProductService
from app.states.operation_state import OperationState


def message(text):
    return SimpleNamespace(text=text, answer=AsyncMock(), from_user=SimpleNamespace(full_name="Тест"))


def callback(data):
    return SimpleNamespace(
        data=data, answer=AsyncMock(), message=SimpleNamespace(edit_text=AsyncMock(), answer=AsyncMock())
    )


class OperationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.storage = MemoryStorage()
        self.state = FSMContext(self.storage, StorageKey(bot_id=1, chat_id=1, user_id=1))
        self.session = AsyncMock(spec=AsyncSession)
        self.session.__aenter__.return_value = self.session
        self.session.get.return_value = Product(id=2, name="Контроллер", quantity=0)
        self.repository = OperationRepository(MagicMock(return_value=self.session))
        self.service = OperationService(self.repository)
        self.products = AsyncMock(spec=ProductService)
        self.products.get_products.return_value = [
            Product(id=1, name="Контроллер", article="001"),
            Product(id=2, name="Контроллер", article="002"),
        ]

    async def asyncTearDown(self):
        await self.storage.close()

    async def fill(self, kind="receipt"):
        await handlers.start_add_operation(message("Внести поступления/отгрузку"), self.state, self.products)
        key = (await self.state.get_data())["operation_selection"]
        await handlers.product_chosen(callback(f"op_product:{key}:2"), self.state)
        await handlers.type_chosen(callback(f"op_type:{key}:{kind}"), self.state)
        await handlers.get_quantity(message("10"), self.state)

    async def test_receipt_and_shipment_keep_product_link(self):
        for kind, label in (("receipt", "Поступление"), ("shipment", "Отгрузка")):
            await self.fill(kind)
            self.assertEqual(await self.state.get_state(), OperationState.comment.state)
            self.session.add.reset_mock()
            self.session.commit.reset_mock()
            reply = message("-")
            await handlers.get_comment(reply, self.state, self.service)
            self.session.add.assert_called_once()
            operation = self.session.add.call_args.args[0]
            self.assertIsInstance(operation, Operation)
            self.assertEqual((operation.product_id, operation.op_type, operation.quantity), (2, label, 10))
            self.assertNotIn("responsible", Operation.__table__.c)
            self.assertEqual(self.session.get.return_value.quantity, 10 if kind == "receipt" else 0)
            self.session.get.assert_awaited_with(Product, 2, with_for_update=True)
            self.session.commit.assert_awaited_once()
            self.assertIsNone(await self.state.get_state())
        fk = next(iter(Operation.__table__.c.product_id.foreign_keys))
        self.assertEqual(fk.target_fullname, "products.id")
        self.assertEqual(fk.ondelete, "RESTRICT")

    async def test_same_name_products_have_different_buttons(self):
        reply = message("Внести поступления/отгрузку")
        await handlers.start_add_operation(reply, self.state, self.products)
        rows = reply.answer.call_args.kwargs["reply_markup"].inline_keyboard
        self.assertNotEqual(rows[0][0].text, rows[1][0].text)
        self.assertNotEqual(rows[0][0].callback_data, rows[1][0].callback_data)
        self.session.add.assert_not_called()

    async def test_empty_or_unavailable_products(self):
        self.products.get_products.return_value = []
        await handlers.start_add_operation(message("start"), self.state, self.products)
        self.assertIsNone(await self.state.get_state())
        self.products.get_products.side_effect = ProductReadError()
        with self.assertLogs("app.handlers.operation", level="ERROR"):
            await handlers.start_add_operation(message("start"), self.state, self.products)
        self.assertIsNone(await self.state.get_state())

    async def test_stale_and_unknown_callbacks_are_rejected(self):
        await handlers.start_add_operation(message("start"), self.state, self.products)
        key = (await self.state.get_data())["operation_selection"]
        for data in ("op_product:old:2", f"op_product:{key}:999", "op_product:bad"):
            reply = callback(data)
            await handlers.product_chosen(reply, self.state)
            reply.answer.assert_awaited_once_with("Этот выбор уже недоступен.")
        self.assertEqual(await self.state.get_state(), OperationState.product.state)
        await handlers.product_chosen(callback(f"op_product:{key}:2"), self.state)
        await handlers.type_chosen(callback(f"op_type:{key}:unknown"), self.state)
        self.assertEqual(await self.state.get_state(), OperationState.op_type.state)

    async def test_invalid_quantity_and_comment_do_not_save(self):
        await self.state.set_state(OperationState.quantity)
        for value in (None, "abc", "0", "-1", "1.5", "²", str(2**63)):
            await handlers.get_quantity(message(value), self.state)
            self.assertEqual(await self.state.get_state(), OperationState.quantity.state)
        await self.fill()
        for value in (None, " ", "\x00"):
            await handlers.get_comment(message(value), self.state, self.service)
            self.assertEqual(await self.state.get_state(), OperationState.comment.state)
        self.session.add.assert_not_called()

    async def test_missing_product_does_not_save(self):
        self.session.get.return_value = None
        with self.assertRaises(ValueError):
            await self.service.add_operation(2, "Поступление", 10, "-")
        self.session.add.assert_not_called()

    async def test_failed_save_keeps_state(self):
        await self.fill()
        self.session.commit.side_effect = SQLAlchemyError("Unavailable")
        reply = message("-")
        with self.assertLogs("app.handlers.operation", level="ERROR"):
            await handlers.get_comment(reply, self.state, self.service)
        self.assertEqual(await self.state.get_state(), OperationState.comment.state)
        self.assertNotIn("успешно", reply.answer.call_args.args[0])
