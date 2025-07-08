from typing import AsyncGenerator, Generator
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from .config import get_settings

settings = get_settings()
engine = create_async_engine(settings.DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLModel session."""
    async with async_session() as session:
        yield session


async def init_db() -> None:
    """Create database tables asynchronously."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

# --- Synchronous engine and session for non-async tasks ---
# Some components such as background jobs may use a regular SQLAlchemy session.
# The DATABASE_URL may specify an async driver (e.g. "sqlite+aiosqlite").
# For the synchronous engine we strip any async driver suffix.
sync_database_url = settings.DATABASE_URL.replace("+aiosqlite", "").replace("+asyncpg", "")
sync_engine = create_engine(sync_database_url, echo=False, future=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Yield a synchronous SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
