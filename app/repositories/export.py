from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import aliased

from app.models import Employee, Operation, Product, ProductComponent


class ExportReadError(Exception):
    """Не удалось получить данные для выгрузки."""


class ExportRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self.sessions = sessions

    async def get_all(self) -> dict[str, list[dict]]:
        try:
            async with self.sessions() as session:
                employees = await session.execute(
                    select(Employee.id, Employee.telegram_id, Employee.name)
                    .order_by(Employee.id)
                )
                products = await session.execute(
                    select(
                        Product.id, Product.article, Product.name, Product.price,
                        Product.quantity, Product.comment, Product.kind, Product.responsible,
                    ).order_by(Product.id)
                )
                operations = await session.execute(
                    select(
                        Operation.id, Operation.product_id, Product.name,
                        Product.article, Operation.op_type, Operation.quantity,
                        Operation.comment, Operation.created_at,
                    )
                    .join(Product, Product.id == Operation.product_id)
                    .order_by(Operation.created_at.desc(), Operation.id.desc())
                )
                component = aliased(Product)
                compositions = await session.execute(
                    select(
                        ProductComponent.product_id, Product.article.label("product_article"),
                        Product.name.label("product_name"), ProductComponent.component_id,
                        component.article.label("component_article"),
                        component.name.label("component_name"), ProductComponent.quantity,
                    )
                    .join(Product, Product.id == ProductComponent.product_id)
                    .join(component, component.id == ProductComponent.component_id)
                    .order_by(ProductComponent.product_id, ProductComponent.component_id)
                )
                return {
                    "employees": [dict(row) for row in employees.mappings().all()],
                    "products": [dict(row) for row in products.mappings().all()],
                    "operations": [dict(row) for row in operations.mappings().all()],
                    "components": [dict(row) for row in compositions.mappings().all()],
                }
        except (SQLAlchemyError, OSError, TimeoutError) as error:
            raise ExportReadError("Не удалось получить данные для выгрузки") from error
