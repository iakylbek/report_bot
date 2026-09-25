from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.models import Base


def create_engine(database_url: str) -> AsyncEngine:
    url = make_url(database_url).set(drivername="postgresql+asyncpg")
    return create_async_engine(
        url, pool_pre_ping=True,
        connect_args={"timeout": 10, "command_timeout": 10},
    )


async def create_tables(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
