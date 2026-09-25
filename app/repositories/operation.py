from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Operation, Product


class OperationSaveError(Exception):
    """Не удалось сохранить операцию."""


class OperationReadError(Exception):
    """Не удалось загрузить операции."""


class OperationRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self.sessions = sessions

    async def get_page(
        self, op_type: str, product_id: int | None, page: int, page_size: int,
        since: datetime, until: datetime,
    ) -> tuple[list[dict], bool]:
        query = (
            select(
                Operation.id, Operation.created_at, Operation.quantity,
                Operation.comment, Operation.product_id,
                Product.name, Product.article,
            )
            .join(Product, Product.id == Operation.product_id)
            .where(
                Operation.op_type == op_type,
                Operation.created_at >= since, Operation.created_at <= until,
            )
            .order_by(Operation.created_at.desc(), Operation.id.desc())
            .offset(page * page_size).limit(page_size + 1)
        )
        if product_id is not None:
            query = query.where(Operation.product_id == product_id)
        try:
            async with self.sessions() as session:
                result = await session.execute(query)
                rows = [dict(row) for row in result.mappings().all()]
                return rows[:page_size], len(rows) > page_size
        except (SQLAlchemyError, OSError, TimeoutError) as error:
            raise OperationReadError("Не удалось загрузить операции") from error

    async def add(
        self, product_id: int, op_type: str, quantity: int, comment: str,
        stock_change: int,
    ) -> None:
        try:
            async with self.sessions() as session:
                # Блокируем строку до commit, чтобы параллельные операции не теряли изменения.
                product = await session.get(Product, product_id, with_for_update=True)
                if product is None:
                    raise ValueError("Товар больше не существует. Начните ввод операции заново.")
                product.quantity += stock_change
                session.add(Operation(
                    product_id=product_id, op_type=op_type, quantity=quantity, comment=comment,
                ))
                await session.commit()
        except (SQLAlchemyError, OSError, TimeoutError) as error:
            raise OperationSaveError("Не удалось сохранить операцию") from error
