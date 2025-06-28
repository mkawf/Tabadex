# tabadex_bot/database/session.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from tabadex_bot.config import settings

# Create a synchronous engine (optional, can be useful for scripts)
sync_engine = create_engine(settings.DATABASE_URL)

# Create an asynchronous engine for the main application
async_engine = create_async_engine(settings.DATABASE_URL, echo=False)

# Create a configured "Session" class for async sessions
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db_session() -> AsyncSession:
    """Dependency to get a new database session."""
    async with AsyncSessionLocal() as session:
        yield session