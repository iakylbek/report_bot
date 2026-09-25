import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from itertools import count

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import create_engine, select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.handlers.remains import show_remains
from app.models import Base, Operation, Product
from app.repositories.product import ProductReadError, ProductRepository
from app.services.product import ProductService
from app.repositories.operation import OperationRepository, OperationSaveError
from app.services.operation import OperationService


class RemainsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Выполняем ORM-запрос на SQLite в памяти, без внешней базы.
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.execute.side_effect = self.db.execute
        self.session = session
        self.service = ProductService(ProductRepository(MagicMock(return_value=session)))
        self.storage = MemoryStorage()
        self.state = FSMContext(self.storage, StorageKey(bot_id=1, chat_id=1, user_id=1))
        self.message = SimpleNamespace(answer=AsyncMock())

    async def asyncTearDown(self):
        self.db.close()
        self.engine.dispose()
        await self.storage.close()

    def seed(self):
        for product_id, quantity in ((1, 11), (2, -2), (3, 0)):
            self.db.add(Product(
                id=product_id, article="001", name="Контроллер",
                price=Decimal("10.50"), comment="-", quantity=quantity,
            ))
        self.db.flush()
        for index, (product_id, op_type, quantity) in enumerate([
            (1, "Поступление", 10), (1, "Поступление", 5), (1, "Отгрузка", 4),
            (2, "Отгрузка", 2),
        ], 1):
            self.db.add(Operation(
                id=index, product_id=product_id, op_type=op_type,
                quantity=quantity, comment="-",
            ))
        self.db.commit()

    async def test_reads_saved_quantities_without_operations(self):
        self.seed()
        # Остатки должны читаться из products даже без журнала операций.
        for operation in self.db.scalars(select(Operation)).all():
            self.db.delete(operation)
        self.db.commit()
        rows = await self.service.get_remains()
        self.assertEqual([(row["id"], row["quantity"]) for row in rows], [(1, 11), (2, -2), (3, 0)])

    async def test_report_and_state_reset(self):
        self.seed()
        await self.state.set_state("unfinished")
        await self.state.update_data(article="old")
        await show_remains(self.message, self.state, self.service)
        text = self.message.answer.call_args.args[0]
        self.assertIn("(ID 1): 11 шт.", text)
        self.assertIn("(ID 3): 0 шт.", text)
        self.assertIn("Отгрузок больше поступлений", text)
        self.assertIn("Всего по учёту: 9 шт.", text)
        self.assertEqual(await self.state.get_data(), {})
        self.assertIsNone(await self.state.get_state())

    def operation_service(self):
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.get.side_effect = self.db.get
        session.commit.side_effect = self.db.commit
        ids = count(1)

        def add(operation):
            operation.id = next(ids)
            self.db.add(operation)

        async def close(exc_type, exc, traceback):
            if exc_type:
                self.db.rollback()
            return False

        session.add = MagicMock(side_effect=add)
        session.__aexit__.side_effect = close
        return OperationService(OperationRepository(MagicMock(return_value=session))), session

    async def test_new_product_zero_and_operations_update_quantity(self):
        product = Product(id=1, article="001", name="Товар", price=Decimal("10"), comment="-")
        self.db.add(product)
        self.db.commit()
        self.assertEqual(product.quantity, 0)
        service, session = self.operation_service()
        await service.add_operation(1, "Поступление", 10, "-")
        await service.add_operation(1, "Отгрузка", 4, "-")
        self.db.expire_all()
        self.assertEqual(self.db.get(Product, 1).quantity, 6)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Operation)), 2)
        session.get.assert_awaited_with(Product, 1, with_for_update=True)

    async def test_failed_operation_rolls_back_quantity_and_journal(self):
        self.db.add(Product(id=1, article="001", name="Товар", price=Decimal("10"), comment="-"))
        self.db.commit()
        service, session = self.operation_service()

        def fail_commit():
            self.db.flush()
            raise SQLAlchemyError("Failure after flush")

        session.commit.side_effect = fail_commit
        with self.assertRaises(OperationSaveError):
            await service.add_operation(1, "Поступление", 10, "-")
        self.db.expire_all()
        self.assertEqual(self.db.get(Product, 1).quantity, 0)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(Operation)), 0)

    async def test_database_error(self):
        self.session.execute.side_effect = SQLAlchemyError("Unavailable")
        with self.assertLogs("app.handlers.remains", level="ERROR"):
            await show_remains(self.message, self.state, self.service)
        self.assertIn("Не удалось загрузить", self.message.answer.call_args.args[0])

    async def test_large_report_is_split(self):
        service = AsyncMock(spec=ProductService)
        service.get_remains.return_value = [
            {"id": i, "name": "📦" * 180, "article": "А" * 80, "quantity": 1}
            for i in range(40)
        ]
        await show_remains(self.message, self.state, service)
        self.assertGreater(self.message.answer.await_count, 1)
        for call in self.message.answer.call_args_list:
            self.assertLessEqual(len(call.args[0].encode("utf-8")), 3500)
        self.assertIn("Всего по учёту: 40 шт.", self.message.answer.call_args.args[0])
