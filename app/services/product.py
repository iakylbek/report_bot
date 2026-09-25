from decimal import Decimal

from app.models import Product
from app.repositories.product import ProductRepository


def validate_text(value: str | None) -> str:
    text = (value or "").strip()
    if not text or "\x00" in text:
        raise ValueError("Введите непустой текст. Попробуйте снова:")
    return text


def parse_price(value: str | None) -> Decimal:
    text = (value or "").strip()
    if not text.isascii() or not text.replace(".", "", 1).isdigit():
        raise ValueError("Цена должна быть неотрицательным числом, например 125.50:")
    return Decimal(text)


def parse_quantity(value: str | None) -> int:
    text = (value or "").strip()
    if not text.isascii() or not text.isdigit() or len(text) > 19:
        raise ValueError("Количество должно быть положительным целым числом. Попробуйте снова:")
    quantity = int(text)
    if not 0 < quantity <= 2**63 - 1:
        raise ValueError("Количество некорректно. Проверьте число и введите снова:")
    return quantity


class ProductService:
    def __init__(self, repository: ProductRepository) -> None:
        self.repository = repository

    async def get_products(self) -> list[Product]:
        return await self.repository.get_all()

    async def get_components(self) -> list[Product]:
        return await self.repository.get_all(kind="component")

    async def get_products_page(self, page: int = 0) -> tuple[list[Product], bool]:
        if page < 0 or page > 1_000_000:
            raise ValueError("Некорректная страница.")
        return await self.repository.get_page(page, 10)

    async def get_remains(self) -> list[dict]:
        return await self.repository.get_remains()

    async def add_component(
        self, article: str, name: str, price: str, comment: str, responsible: str,
    ) -> None:
        await self.repository.add(
            article=validate_text(article),
            name=validate_text(name),
            price=parse_price(price),
            comment=validate_text(comment),
            responsible=validate_text(responsible),
        )

    async def add_product(self, article: str, name: str, components: dict[int, int]) -> None:
        article, name = validate_text(article), validate_text(name)
        if not components:
            raise ValueError("Добавьте хотя бы одну комплектующую.")
        for component_id, quantity in components.items():
            if type(component_id) is not int or not 0 < component_id <= 2**63 - 1:
                raise ValueError("Некорректная комплектующая.")
            if type(quantity) is not int:
                raise ValueError("Количество должно быть целым числом.")
            parse_quantity(str(quantity))
        await self.repository.add_product(article, name, components)
