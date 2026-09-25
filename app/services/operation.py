from datetime import datetime, timedelta, timezone

from app.repositories.operation import OperationRepository
from app.services.product import parse_quantity, validate_text


class OperationService:
    def __init__(self, repository: OperationRepository) -> None:
        self.repository = repository

    async def get_shipments(
        self, page: int = 0, product_id: int | None = None, period: str = "month"
    ) -> tuple[list[dict], bool]:
        return await self.get_page("Отгрузка", page, product_id, period)

    async def get_receipts(
        self, page: int = 0, product_id: int | None = None, period: str = "month"
    ) -> tuple[list[dict], bool]:
        return await self.get_page("Поступление", page, product_id, period)

    async def get_page(
        self, op_type: str, page: int, product_id: int | None, period: str
    ) -> tuple[list[dict], bool]:
        if op_type not in ("Поступление", "Отгрузка"):
            raise ValueError("Неизвестный тип операции.")
        if page < 0 or page > 1_000_000:
            raise ValueError("Некорректная страница.")
        if product_id is not None and not 0 < product_id <= 2**63 - 1:
            raise ValueError("Некорректный товар.")
        days = {"week": 7, "month": 30}
        if period not in days:
            raise ValueError("Некорректный период.")
        now = datetime.now(timezone.utc)
        return await self.repository.get_page(
            op_type, product_id, page, 10, now - timedelta(days=days[period]), now
        )

    async def add_operation(
        self, product_id: int, op_type: str, quantity: int, comment: str,
    ) -> None:
        if op_type not in ("Поступление", "Отгрузка"):
            raise ValueError("Неизвестный тип операции.")
        quantity = parse_quantity(str(quantity))
        stock_change = quantity if op_type == "Поступление" else -quantity
        await self.repository.add(
            product_id, op_type, quantity, validate_text(comment), stock_change
        )
