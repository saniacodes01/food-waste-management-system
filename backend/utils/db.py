from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from utils.config import settings

_connect_args = {}
if settings.db_schema:
    # route every connection at this schema (falls back to public for PostGIS)
    _connect_args["server_settings"] = {"search_path": f"{settings.db_schema},public"}

engine = create_async_engine(settings.database_url, echo=False, connect_args=_connect_args)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        if settings.db_schema:
            await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.db_schema}"'))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        from models import User, Donation, DonationEvent, Feedback  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
