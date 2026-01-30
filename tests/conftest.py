import os
# Set env var before importing app config which instantiates Settings
os.environ["LITELLM_MASTER_KEY"] = "sk-test"

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from app.main import app
from app.database import get_session
from app.litellm_client import litellm_client
from unittest.mock import AsyncMock

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture(name="mock_litellm")
def mock_litellm_fixture():
    # Mock methods
    litellm_client.get_user_info = AsyncMock()
    litellm_client.create_user = AsyncMock()
    litellm_client.list_keys = AsyncMock()
    litellm_client.generate_key = AsyncMock()
    litellm_client.delete_key = AsyncMock()
    return litellm_client
