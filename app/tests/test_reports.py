import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram import Bot, Dispatcher
from aiogram.types import CallbackQuery, Chat, Message, Update, User
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.handlers.operation_report import format_operations, report_router
from app.keyboards.report_kb import (
    TITLES, ReceiptPage, ShipmentPage, get_page_keyboard, get_products_keyboard,
)
from app.models import Base, Operation, Product
from app.repositories.operation import OperationReadError, OperationRepository
from app.repositories.product import ProductRepository
from app.services.operation import OperationService
from app.services.product import ProductService


class ReportTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.db.close)
        self.session = AsyncMock()
        self.session.__aenter__.return_value = self.session
        self.session.execute.side_effect = self.db.execute
        self.session.scalars.side_effect = self.db.scalars
        sessions = MagicMock(return_value=self.session)
        self.operations = OperationService(OperationRepository(sessions))
        self.products = ProductService(ProductRepository(sessions))
        self.getters = (self.operations.get_receipts, self.operations.get_shipments)
        self.now = datetime.now(timezone.utc)
        for index in range(1, 13):
            self.db.add(Product(id=index, name="Товар", article=str(index), price=10, comment="-"))
        self.db.flush()
        for offset, op_type in ((0, "Поступление"), (100, "Отгрузка")):
            for index in range(1, 22):
                self.db.add(Operation(
                    id=offset + index, product_id=1 if index % 2 else 2,
                    op_type=op_type, quantity=index, comment="Тест",
                    created_at=self.now - timedelta(days=8 - index // 3),
                ))
        self.db.commit()

    async def test_order_pagination_and_product_filter(self):
        for get_page in self.getters:
            with self.subTest(report=get_page.__name__):
                pages = [await get_page(page=i) for i in range(3)]
                self.assertEqual([len(rows) for rows, _ in pages], [10, 10, 1])
                self.assertEqual([more for _, more in pages], [True, True, False])
                self.assertEqual([r["quantity"] for rows, _ in pages for r in rows], list(range(21, 0, -1)))
                first, more = await get_page(product_id=1)
                last, last_more = await get_page(page=1, product_id=1)
                self.assertTrue(more)
                self.assertFalse(last_more)
                self.assertEqual([r["quantity"] for r in first + last], list(range(21, 0, -2)))
                self.assertTrue(all(r["product_id"] == 1 for r in first + last))
                self.assertEqual(await get_page(product_id=3), ([], False))
                self.assertEqual(await get_page(page=3), ([], False))

    async def test_period_boundaries(self):
        dates = [self.now, self.now - timedelta(days=7),
                 self.now - timedelta(days=7, microseconds=1), self.now - timedelta(days=30),
                 self.now - timedelta(days=30, microseconds=1), self.now + timedelta(seconds=1)]
        for offset, op_type in ((200, "Поступление"), (300, "Отгрузка")):
            for index, date in enumerate(dates, 1):
                self.db.add(Operation(id=offset + index, product_id=3, op_type=op_type,
                                      quantity=index, comment="-", created_at=date))
        self.db.commit()
        with patch("app.services.operation.datetime") as clock:
            clock.now.return_value = self.now
            for get_page in self.getters:
                with self.subTest(report=get_page.__name__):
                    week, _ = await get_page(product_id=3, period="week")
                    month, _ = await get_page(product_id=3, period="month")
                    self.assertEqual([r["quantity"] for r in week], [1, 2])
                    self.assertEqual([r["quantity"] for r in month], [1, 2, 3, 4])

    async def test_invalid_parameters_and_database_error(self):
        for get_page in self.getters:
            for kwargs in ({"page": -1}, {"page": 1_000_001}, {"product_id": -1},
                           {"product_id": 2**63}, {"period": "unknown"}):
                with self.subTest(report=get_page.__name__, **kwargs), self.assertRaises(ValueError):
                    await get_page(**kwargs)
        self.session.execute.side_effect = SQLAlchemyError("Unavailable")
        for get_page in self.getters:
            with self.assertRaises(OperationReadError):
                await get_page()

    async def test_product_picker_and_navigation(self):
        first, more = await self.products.get_products_page()
        last, last_more = await self.products.get_products_page(1)
        self.assertEqual([p.id for p in first + last], list(range(1, 13)))
        self.assertTrue(more)
        self.assertFalse(last_more)
        for kind, page_type in (("receipt", ReceiptPage), ("ship", ShipmentPage)):
            with self.subTest(kind=kind):
                picker = get_products_keyboard(kind, first, 0, more)
                self.assertEqual(picker.inline_keyboard[1][0].callback_data, f"{kind}_period:2")
                keyboard = get_page_keyboard(kind, 2, 1, True, "week")
                callbacks = [page_type.unpack(b.callback_data) for b in keyboard.inline_keyboard[0]]
                self.assertEqual([(c.product_id, c.page, c.period) for c in callbacks],
                                 [(2, 0, "week"), (2, 2, "week")])
                self.assertEqual(len(get_page_keyboard(kind, 0, 0, False, "month").inline_keyboard), 2)

    async def test_format_moscow_time_and_message_limit(self):
        row = {"name": "Контроллер", "article": "001", "quantity": 5, "comment": "Приёмка"}
        dates = [datetime(2026, 9, 24, 22, 30, tzinfo=timezone.utc), datetime(2026, 9, 24, 22, 30),
                 datetime(2026, 9, 25, 4, 30, tzinfo=timezone(timedelta(hours=6)))]
        for title in TITLES.values():
            for date in dates:
                row["created_at"] = date
                text = format_operations([row], 0, 0, title, "Нет записей")
                self.assertIn("Контроллер - 001\n25.09.2026 01:30 · 5 шт. · Приёмка", text)
                self.assertNotIn("UTC", text)
            long_row = dict(row, name="📦" * 4000, article="📦" * 4000, comment="📦" * 4000, quantity=2**63 - 1)
            text = format_operations([long_row] * 10, 1_000_000, 2**63 - 1, title, "Нет записей")
            self.assertLessEqual(len((text + "\n\nПериод: последние 30 дней").encode("utf-16-le")) // 2, 4096)

    async def test_dispatcher_menus_and_callbacks(self):
        dispatcher = Dispatcher()
        dispatcher.include_router(report_router)
        bot = Bot(token="123456:LOCAL_TEST_TOKEN")
        user = User(id=1, is_bot=False, first_name="Тест")
        context = dispatcher.fsm.get_context(bot=bot, chat_id=1, user_id=1)
        try:
            with (patch.object(Message, "answer", new_callable=AsyncMock) as answer,
                  patch.object(Message, "edit_text", new_callable=AsyncMock) as edit,
                  patch.object(CallbackQuery, "answer", new_callable=AsyncMock) as ack):
                for kind, title in TITLES.items():
                    message = Message(message_id=1, date=self.now, chat=Chat(id=1, type="private"), from_user=user, text=title)
                    await context.set_state("unfinished")
                    answer.reset_mock()
                    await dispatcher.feed_update(bot, Update(update_id=1, message=message))
                    answer.assert_awaited_once()
                    self.assertIsNone(await context.get_state())
                    cases = [(f"{kind}_period:0", "Выберите период"),
                             (f"{kind}_period:2", "Выберите период"),
                             (f"{kind}:0:0:month", "21 шт."),
                             (f"{kind}:0:1:month", "11 шт."),
                             (f"{kind}:0:0:week", "последние 7 дней"),
                             (f"{kind}_products:0", "Выберите товар"),
                             (f"{kind}:2:0:month", f"{title} товара ID 2"),
                             (f"{kind}:3:0:month", "пока нет"),
                             (f"{kind}_menu", "Выберите вариант")]
                    for data, expected in cases:
                        with self.subTest(data=data):
                            edit.reset_mock()
                            ack.reset_mock()
                            callback = CallbackQuery(id=data, from_user=user, message=message, chat_instance="test", data=data)
                            await dispatcher.feed_update(bot, Update(update_id=2, callback_query=callback),
                                                         operation_service=self.operations, product_service=self.products)
                            ack.assert_awaited_once()
                            edit.assert_awaited_once()
                            self.assertIn(expected, edit.call_args.args[0])
        finally:
            await dispatcher.storage.close()
            await bot.session.close()
