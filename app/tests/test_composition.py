import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy import create_engine, select, event
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.handlers import product as handlers
from app.keyboards.product_kb import get_components_keyboard
from app.models import Base, Product, ProductComponent
from app.repositories.product import ProductRepository, ProductSaveError
from app.services.employee import EmployeeService
from app.services.product import ProductService


def message(text):
    return SimpleNamespace(text=text, answer=AsyncMock())


def callback(data):
    return SimpleNamespace(data=data, answer=AsyncMock(), message=SimpleNamespace(
        answer=AsyncMock(), edit_text=AsyncMock(), edit_reply_markup=AsyncMock(),
    ))


class CompositionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_engine("sqlite:///:memory:")

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.db.add_all([
            Product(id=i, article=f"00{i}", name="Деталь", price=Decimal("10"),
                    comment="-", kind="component", responsible="Анна", quantity=5)
            for i in (1, 2)
        ])
        self.db.add(Product(id=3, article="P", name="Продукт", price=0, comment="-", kind="product"))
        self.db.commit()
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.scalars.side_effect = self.db.scalars
        session.commit.side_effect = self.db.commit

        def add(product):
            product.id = 100  # SQLite не генерирует Identity для BigInteger.
            self.db.add(product)

        async def close(exc_type, exc, traceback):
            if exc_type:
                self.db.rollback()
            return False

        session.add = MagicMock(side_effect=add)
        session.__aexit__.side_effect = close
        self.session = session
        self.service = ProductService(ProductRepository(MagicMock(return_value=session)))
        self.employees = AsyncMock(spec=EmployeeService)
        self.employees.get_names.return_value = ["Анна", "Борис"]
        self.storage = MemoryStorage()
        self.state = FSMContext(self.storage, StorageKey(bot_id=1, chat_id=1, user_id=1))

    async def asyncTearDown(self):
        await self.storage.close()
        self.db.close()
        self.engine.dispose()

    async def begin(self, kind="product"):
        await handlers.start_add_product(message("Добавить товар"), self.state)
        key = (await self.state.get_data())["catalog_selection"]
        await handlers.choose_kind(callback(f"catalog_kind:{key}:{kind}"), self.state, self.service, self.employees)

    async def select(self, component_id, quantity):
        key = (await self.state.get_data())["catalog_selection"]
        await handlers.choose_component(callback(f"catalog_component:{key}:{component_id}"), self.state)
        await handlers.get_component_quantity(message(str(quantity)), self.state)

    async def test_complete_product_dialog_saves_links_without_changing_stock(self):
        await self.begin()
        await handlers.get_article(message("NEW"), self.state)
        await handlers.get_name(message("Новый продукт"), self.state)
        await self.select(1, 2)
        await self.select(2, 3)
        await self.select(1, 4)  # Повторный выбор заменяет количество.
        key = (await self.state.get_data())["catalog_selection"]
        save = callback(f"catalog_save:{key}:done")
        await handlers.save_product(save, self.state, self.service)
        self.assertIsNone(await self.state.get_state())
        product = self.db.get(Product, 100)
        self.assertEqual((product.kind, product.quantity, product.price, product.responsible), ("product", 0, 0, None))
        self.assertEqual({c.component_id: c.quantity for c in product.components}, {1: 4, 2: 3})
        self.assertEqual([self.db.get(Product, i).quantity for i in (1, 2)], [5, 5])
        await handlers.save_product(save, self.state, self.service)
        self.session.commit.assert_awaited_once()

    async def test_only_components_can_be_selected(self):
        self.assertEqual([p.id for p in await self.service.get_components()], [1, 2])
        for selected in ({3: 1}, {999: 1}):
            with self.assertRaises(ValueError):
                await self.service.add_product("P", "Продукт", selected)
        self.session.add.assert_not_called()

    async def test_invalid_composition_is_rejected(self):
        for selected in ({}, {1: 0}, {1: -1}, {1: 1.5}, {1: 2**63}, {-1: 1}):
            with self.assertRaises(ValueError):
                await self.service.add_product("P", "Продукт", selected)
        self.session.commit.assert_not_awaited()

    async def test_save_failure_rolls_back_product_and_composition(self):
        def fail_commit():
            self.db.flush()
            raise SQLAlchemyError("Failed commit")
        self.session.commit.side_effect = fail_commit
        with self.assertRaises(ProductSaveError):
            await self.service.add_product("P", "Продукт", {1: 1, 2: 2})
        self.assertIsNone(self.db.get(Product, 100))
        self.assertEqual(list(self.db.scalars(select(ProductComponent))), [])

    async def test_used_component_cannot_be_deleted(self):
        await self.service.add_product("P", "Продукт", {1: 1})
        self.db.delete(self.db.get(Product, 1))
        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    async def test_stale_callback_and_invalid_quantity_keep_state(self):
        await self.begin()
        await handlers.get_article(message("P"), self.state)
        await handlers.get_name(message("Продукт"), self.state)
        old_key = (await self.state.get_data())["catalog_selection"]
        await self.select(1, 2)
        stale = callback(f"catalog_component:{old_key}:2")
        await handlers.choose_component(stale, self.state)
        stale.answer.assert_awaited_with("Этот выбор уже недоступен.")
        key = (await self.state.get_data())["catalog_selection"]
        await handlers.choose_component(callback(f"catalog_component:{key}:2"), self.state)
        for quantity in ("0", "-1", "1.5", "abc"):
            await handlers.get_component_quantity(message(quantity), self.state)
            self.assertEqual(await self.state.get_state(), handlers.ProductState.component_quantity.state)
        self.assertEqual((await self.state.get_data())["selected"], {"1": 2})

    async def test_missing_employees_and_components_keep_kind_selection(self):
        self.employees.get_names.return_value = []
        await self.begin("component")
        self.assertEqual(await self.state.get_state(), handlers.ProductState.kind.state)
        self.session.scalars.side_effect = None
        self.session.scalars.return_value = MagicMock()
        self.session.scalars.return_value.all.return_value = []
        await self.begin("product")
        self.assertEqual(await self.state.get_state(), handlers.ProductState.kind.state)

    async def test_responsible_choice_is_text_and_rejects_old_buttons(self):
        await self.begin("component")
        await handlers.get_article(message("C"), self.state)
        await handlers.get_name(message("Деталь"), self.state)
        await handlers.get_price(message("12.50"), self.state)
        key = (await self.state.get_data())["catalog_selection"]
        choose = callback(f"component_responsible:{key}:1")
        await handlers.get_responsible(choose, self.state)
        self.assertEqual((await self.state.get_data())["responsible"], "Борис")
        await handlers.get_responsible(choose, self.state)
        choose.answer.assert_awaited_with("Этот выбор уже недоступен.")
        await handlers.get_comment(message("-"), self.state, self.service)
        self.assertEqual(self.db.get(Product, 100).responsible, "Борис")
        self.assertFalse(Product.__table__.c.responsible.foreign_keys)

    def test_component_picker_pagination(self):
        choices = {str(i): f"Деталь {i}" for i in range(1, 13)}
        keyboard = get_components_keyboard(choices, {"12": 4}, "key", 1)
        self.assertIn("4 шт.", keyboard.inline_keyboard[1][0].text)
        self.assertEqual(keyboard.inline_keyboard[0][0].callback_data, "catalog_component:key:11")
