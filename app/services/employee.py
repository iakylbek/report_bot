from app.repositories.employee import EmployeeRepository


def parse_telegram_id(value: str | None) -> str:
    value = (value or "").strip()
    if not value.isascii() or not value.isdigit() or not value.strip("0"):
        raise ValueError("ID должен быть положительным целым числом. Попробуйте снова:")
    return value


def validate_name(value: str | None) -> str:
    name = (value or "").strip()
    if not name or "\x00" in name:
        raise ValueError("Введите имя сотрудника текстом:")
    return name


class EmployeeService:
    def __init__(self, repository: EmployeeRepository) -> None:
        self.repository = repository

    async def get_names(self) -> list[str]:
        return await self.repository.get_names()

    async def has_access(self, telegram_id: str) -> bool:
        return await self.repository.exists(parse_telegram_id(telegram_id))

    async def ensure_first_user(self, telegram_id: str) -> None:
        telegram_id = parse_telegram_id(telegram_id)
        if not await self.repository.exists(telegram_id):
            await self.repository.add(telegram_id, "Первый сотрудник")

    async def add_employee(self, telegram_id: str, name: str) -> None:
        telegram_id = parse_telegram_id(telegram_id)
        name = validate_name(name)
        await self.repository.add(telegram_id, name)
