"""Pytest configuration and fixtures."""

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from backend.app.db.database import Base


@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Create an in-memory test database session.
    
    This fixture is useful for repository-level tests that don't need
    the full FastAPI app.
    """
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
    
    # Cleanup
    await engine.dispose()


# Note: The client fixture is defined per-test-file to allow custom cleanup strategies.
# See test_search.py for an example of database cleanup between tests.
