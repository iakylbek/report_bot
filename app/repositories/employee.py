from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Employee


class EmployeeSaveError(Exception):
    """Не удалось сохранить сотрудника."""


class EmployeeReadError(Exception):
    """Не удалось получить список сотрудников."""


class EmployeeRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self.sessions = sessions

    async def exists(self, telegram_id: str) -> bool:
        try:
            async with self.sessions() as session:
                employee_id = await session.scalar(
                    select(Employee.id)
                    .where(func.ltrim(Employee.telegram_id, "0") == telegram_id.lstrip("0"))
                    .limit(1)
                )
                return employee_id is not None
        except (SQLAlchemyError, OSError, TimeoutError) as error:
            raise EmployeeReadError("Не удалось проверить доступ") from error

    async def get_names(self) -> list[str]:
        try:
            async with self.sessions() as session:
                names = await session.scalars(
                    select(Employee.name).distinct().order_by(Employee.name)
                )
                return list(names.all())
        except (SQLAlchemyError, OSError, TimeoutError) as error:
            raise EmployeeReadError("Не удалось получить список сотрудников") from error

    async def add(self, telegram_id: str, name: str) -> None:
        try:
            async with self.sessions() as session:
                session.add(Employee(telegram_id=telegram_id, name=name))
                await session.commit()
        except (SQLAlchemyError, OSError, TimeoutError) as error:
            raise EmployeeSaveError("Не удалось сохранить сотрудника") from error
