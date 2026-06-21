"""
Pytest fixtures for the diary-app integration tests.
Provides: FastAPI TestClient, mock DB session, mock AI service, and test user.
"""
import pytest
import pytest_asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from models import User, Diary
from auth import get_password_hash, create_access_token, get_current_active_user
from main import app

# ── In-memory SQLite for tests ──────────────────────────────────────
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables once per test session."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Provide a clean database session per test, with rollback after."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user and return it."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User):
    """Return Authorization headers for the test user."""
    token = create_access_token(data={"sub": test_user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(db_session: Session):
    """FastAPI TestClient with DB override and test user auth override."""
    app.dependency_overrides[get_db] = lambda: db_session

    async def override_auth():
        user = db_session.query(User).filter(User.username == "testuser").first()
        return user

    app.dependency_overrides[get_current_active_user] = override_auth

    with TestClient(app) as tc:
        yield tc

    app.dependency_overrides.clear()


# ── Mock AI service fixture ─────────────────────────────────────────
@pytest.fixture
def mock_ai_service():
    """Mock the AI service to return a controlled response."""
    async def mock_stream():
        yield {
            "original": "This is a test sentence.",
            "corrected": "This is a test sentence.",
            "explanation": "No errors found.",
            "suggestions": ["This is a sample sentence."],
        }
        yield {"type": "optimized", "optimized_content": "This is a test sentence."}

    with patch("main.ai_service") as mock_ai:
        mock_ai.correct_diary = AsyncMock(return_value={
            "corrections": [
                {
                    "original": "This is a test sentence.",
                    "corrected": "This is a test sentence.",
                    "explanation": "No errors found.",
                    "suggestions": ["This is a sample sentence."],
                }
            ],
            "optimized_content": "This is a test sentence.",
        })
        mock_ai.correct_diary_stream = mock_stream
        mock_ai.search_phrase = AsyncMock(return_value={
            "phrase": "test",
            "translations": ["测试"],
            "examples": ["This is a test."],
            "alternatives": ["trial"],
        })
        yield mock_ai


@pytest.fixture
def mock_ai_service_error():
    """Mock the AI service to simulate an API failure."""
    with patch("main.ai_service") as mock_ai:
        mock_ai.correct_diary = AsyncMock(return_value={
            "corrections": [],
            "optimized_content": "original text",
            "error": "AI API error: 500 - Internal Server Error",
        })
        yield mock_ai


@pytest.fixture
def mock_ai_service_empty():
    """Mock the AI service returning empty corrections (simulating the bug)."""
    with patch("main.ai_service") as mock_ai:
        mock_ai.correct_diary = AsyncMock(return_value={
            "corrections": [],
            "optimized_content": "",
        })
        yield mock_ai


@pytest.fixture
def mock_ai_service_401():
    """Mock the AI service to simulate API key expired (401)."""
    with patch("main.ai_service") as mock_ai:
        mock_ai.correct_diary = AsyncMock(return_value={
            "corrections": [],
            "optimized_content": "Something I wrote.",
            "error": "AI API error: 401 - " + '{"error":{"code":"401","message":"令牌已过期或验证不正确"}}',
        })
        yield mock_ai