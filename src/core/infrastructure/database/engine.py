from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio.engine import AsyncEngine, create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession

from core.settings import DatabaseSettings


def build_engine(settings: DatabaseSettings, *, echo: bool = False) -> AsyncEngine:
    """Create the async engine from settings.

    Connection is lazy — nothing is opened here, so calling this never touches
    the database (and never fails on an unreachable DB).
    """
    return create_async_engine(
        settings.SQLALCHEMY_DATABASE_URI,
        echo=echo,
        pool_pre_ping=True,
    )


def build_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create a session factory bound to ``engine``."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
