"""Pytest configuration and fixtures."""
import pytest
from sqlmodel import SQLModel, create_engine, Session
from fastapi.testclient import TestClient
from backend.main import app
from backend.db.database import get_session
from backend.core.security import create_access_token


# Test database
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})


def get_test_session():
    """Get test database session."""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="session")
def session_fixture():
    """Create database tables and provide session."""
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create test client."""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_token():
    """Create a test user token."""
    return create_access_token(data={"sub": "1"})


@pytest.fixture
def auth_headers(test_user_token):
    """Create authentication headers."""
    return {"Authorization": f"Bearer {test_user_token}"}
