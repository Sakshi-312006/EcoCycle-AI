"""Pytest fixtures and test environment configuration.

Uses an isolated in-memory SQLite database so tests do not pollute prototype data.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from app.api.deps import get_db
from app.db.base import Base
import app.db.session as db_session
from app.main import create_application

# Isolated in-memory SQLite engine for the test suite
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create all schema tables in test in-memory database."""
    Base.metadata.create_all(bind=test_engine)
    # Patch singleton engine for health probe checks in test environment
    original_engine = db_session._engine
    db_session._engine = test_engine
    yield
    Base.metadata.drop_all(bind=test_engine)
    db_session._engine = original_engine


@pytest.fixture(scope="function")
def db_session_fixture():
    """Yield an isolated database transaction per test function."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="session")
def app():
    """Create a FastAPI application instance with overridden database dependency."""
    app_instance = create_application()

    def _override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app_instance.dependency_overrides[get_db] = _override_get_db
    return app_instance


@pytest.fixture(scope="session")
def client(app) -> TestClient:
    """Synchronous test client fixture."""
    with TestClient(app) as test_client:
        yield test_client
