from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Product, ProductComponent


class ProductSaveError(Exception):
    """Не удалось сохранить товар."""


class ProductReadError(Exception):
    """Не удалось получить товары."""


class ProductRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self.sessions = sessions

    async def get_remains(self) -> list[dict]:
        query = (
            select(
                Product.id, Product.name, Product.article, Product.quantity,
            )
            .order_by(Product.name, Product.id)
        )
        try:
            async with self.sessions() as session:
                result = await session.execute(query)
                return [dict(row) for row in result.mappings().all()]
        except (SQLAlchemyError, OSError, TimeoutError) as error:
            raise ProductReadError("Не удалось получить остатки") from error

    async def get_all(self, kind: str | None = None) -> list[Product]:
        query = select(Product).order_by(Product.name, Product.id)
        if kind is not None:
            query = query.where(Product.kind == kind)
        try:
            async with self.sessions() as session:
                products = await session.scalars(query)
                return list(products.all())
        except (SQLAlchemyError, OSError, TimeoutError) as error:
            raise ProductReadError("Не удалось получить товары") from error

    async def get_page(self, page: int, page_size: int) -> tuple[list[Product], bool]:
        query = (
            select(Product).order_by(Product.name, Product.id)
            .offset(page * page_size).limit(page_size + 1)
        )
        try:
            async with self.sessions() as session:
                result = await session.scalars(query)
                products = list(result.all())
                return products[:page_size], len(products) > page_size
        except (SQLAlchemyError, OSError, TimeoutError) as error:
            raise ProductReadError("Не удалось получить товары") from error

    async def add(
        self, article: str, name: str, price: Decimal, comment: str, responsible: str,
    ) -> None:
        try:
            async with self.sessions() as session:
                session.add(Product(
                    article=article, name=name, price=price,
                    comment=comment, kind="component", responsible=responsible,
                ))
                await session.commit()
        except (SQLAlchemyError, OSError, TimeoutError) as error:
            raise ProductSaveError("Не удалось сохранить товар") from error

    async def add_product(self, article: str, name: str, components: dict[int, int]) -> None:
        try:
            async with self.sessions() as session:
                result = await session.scalars(
                    select(Product).where(Product.id.in_(components))
                    .order_by(Product.id).with_for_update()
                )
                selected = list(result.all())
                if len(selected) != len(components) or any(p.kind != "component" for p in selected):
                    raise ValueError("Состав изменился: выберите существующие комплектующие заново.")
                product = Product(
                    article=article, name=name, kind="product", price=Decimal("0"),
                    comment="-", quantity=0,
                    components=[
                        ProductComponent(component_id=key, quantity=value)
                        for key, value in components.items()
                    ],
                )
                session.add(product)
                await session.commit()
        except (SQLAlchemyError, OSError, TimeoutError) as error:
            raise ProductSaveError("Не удалось сохранить продукт и состав") from error
