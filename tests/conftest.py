import asyncio
from typing import AsyncGenerator
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from app.core.dependencies import get_db
from app.db.base import Base
from app.main import app

# Use a test database suffix or a separate database for testing
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    settings.POSTGRES_DB, f"test_{settings.POSTGRES_DB}"
)

# Create async engine for test db
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Global flag to track if test DB is accessible
_db_offline = False


@pytest.fixture(scope="session", autouse=True)
def initialize_test_db():
    """Create test tables and clean them up after all tests finish."""
    global _db_offline
    try:
        loop = asyncio.get_event_loop_policy().get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    async def setup_db():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    async def teardown_db():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    try:
        loop.run_until_complete(setup_db())
    except Exception as e:
        _db_offline = True
        print(f"\nSkipping DB initialization (Postgres is likely offline): {e}\n")

    yield

    if not _db_offline:
        try:
            loop.run_until_complete(teardown_db())
        except Exception:
            pass


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional test database session."""
    if _db_offline:
        pytest.skip("PostgreSQL database is offline")
        return

    async with TestAsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTPX AsyncClient for FastAPI endpoint testing with db overrides."""

    # Override get_db dependency to use the test session
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()
