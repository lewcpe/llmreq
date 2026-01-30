import pytest
from app.models import KeyHistory
from sqlmodel import select

def test_auth_missing_header(client):
    response = client.get("/api/me")
    assert response.status_code == 401

def test_get_me_jit_create(client, mock_litellm):
    # Setup mock
    mock_litellm.get_user_info.side_effect = [None, {"user_id": "test@example.com", "max_budget": 1.0, "spend": 0.0}]
    mock_litellm.create_user.return_value = {}

    response = client.get("/api/me", headers={"x-forwarded-email": "Test@Example.com"})

    assert response.status_code == 200
    assert response.json()["user_id"] == "test@example.com"
    mock_litellm.create_user.assert_called_once()
    assert mock_litellm.create_user.call_args[1]["user_email"] == "test@example.com"

def test_get_keys_active(client, mock_litellm):
    mock_litellm.get_user_info.return_value = {"user_id": "test@example.com", "spend": 0.0}
    mock_litellm.list_keys.return_value = [
        {"key_alias": "test-key", "token": "sk-hash", "spend": 0.1, "key_name": "test-key"}
    ]

    response = client.get("/api/keys/active", headers={"x-forwarded-email": "test@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["key_name"] == "test-key"
    assert data[0]["spend"] == 0.1

def test_create_key(client, mock_litellm):
    mock_litellm.get_user_info.return_value = {"user_id": "test@example.com", "spend": 0.0}
    mock_litellm.list_keys.return_value = []
    mock_litellm.generate_key.return_value = {"key": "sk-123456789", "token": "token-123"}

    response = client.post("/api/keys", json={"name": "new-key"}, headers={"x-forwarded-email": "test@example.com"})
    assert response.status_code == 200
    assert response.json() == "sk-123456789"

def test_delete_key(client, mock_litellm, session):
    # Need to seed DB first
    db_key = KeyHistory(
        user_id="test@example.com",
        litellm_key_id="token-123",
        key_name="del-key",
        key_mask="sk-...",
        status="active"
    )
    session.add(db_key)
    session.commit()

    mock_litellm.get_user_info.return_value = {"user_id": "test@example.com", "spend": 0.0}
    mock_litellm.delete_key.return_value = True

    response = client.delete("/api/keys/del-key", headers={"x-forwarded-email": "test@example.com"})
    assert response.status_code == 200

    session.refresh(db_key)
    assert db_key.status == "revoked"

def test_key_limits(client, mock_litellm):
    mock_litellm.get_user_info.return_value = {"user_id": "test@example.com", "spend": 0.0}

    # Mock max active keys
    mock_litellm.list_keys.return_value = [{"key_alias": f"key-{i}"} for i in range(10)]

    response = client.post("/api/keys", json={"name": "new-key"}, headers={"x-forwarded-email": "test@example.com"})
    assert response.status_code == 400
    assert "limit reached" in response.json()["detail"]

def test_get_history(client, mock_litellm, session):
    db_key = KeyHistory(
        user_id="test@example.com",
        litellm_key_id="revoked-token",
        key_name="revoked-key",
        key_mask="sk-rev",
        status="revoked"
    )
    session.add(db_key)
    session.commit()

    mock_litellm.get_user_info.return_value = {"user_id": "test@example.com", "spend": 0.0}

    response = client.get("/api/keys/history", headers={"x-forwarded-email": "test@example.com"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["key_name"] == "revoked-key"

def test_sync_keys(client, mock_litellm, session):
    # Setup: LiteLLM has a key that is NOT in DB.
    # Also LiteLLM has a key that IS in DB but status mismatch?

    mock_litellm.get_user_info.return_value = {"user_id": "test@example.com", "spend": 0.0}
    mock_litellm.list_keys.return_value = [
        {"key_alias": "new-key", "token": "sk-new", "spend": 0.0},
        {"key_alias": "existing-key", "token": "sk-exist", "spend": 0.0}
    ]

    # DB has existing-key but revoked
    db_key = KeyHistory(
        user_id="test@example.com",
        litellm_key_id="sk-exist",
        key_name="existing-key",
        key_mask="sk-exist",
        status="revoked"
    )
    session.add(db_key)
    session.commit()

    response = client.get("/api/keys/active", headers={"x-forwarded-email": "test@example.com"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Check "new-key" was added to DB
    stmt = select(KeyHistory).where(KeyHistory.key_name == "new-key")
    new_key = session.exec(stmt).first()
    assert new_key is not None
    assert new_key.status == "active"

    # Check "existing-key" was updated to active
    session.refresh(db_key)
    assert db_key.status == "active"

def test_create_long_term_key_limit(client, mock_litellm, session):
    # DB has 1 long term key (assuming limit is 1)
    db_key = KeyHistory(
        user_id="test@example.com",
        litellm_key_id="lt-1",
        key_name="lt-key",
        key_mask="sk-lt",
        key_type="long-term",
        status="active"
    )
    session.add(db_key)
    session.commit()

    mock_litellm.get_user_info.return_value = {"user_id": "test@example.com", "spend": 0.0}
    mock_litellm.list_keys.return_value = [{"key_alias": "lt-key"}]

    response = client.post("/api/keys", json={"name": "new-lt", "type": "long-term"}, headers={"x-forwarded-email": "test@example.com"})
    assert response.status_code == 400
    assert "limit reached" in response.json()["detail"]

def test_sync_keys_revoke_zombie(client, mock_litellm, session):
    # DB has a key that is active
    # LiteLLM does NOT have it
    db_key = KeyHistory(
        user_id="test@example.com",
        litellm_key_id="zombie-token",
        key_name="zombie-key",
        key_mask="sk-zom",
        status="active"
    )
    session.add(db_key)
    session.commit()

    mock_litellm.get_user_info.return_value = {"user_id": "test@example.com", "spend": 0.0}
    mock_litellm.list_keys.return_value = [] # Empty list from LiteLLM

    response = client.get("/api/keys/active", headers={"x-forwarded-email": "test@example.com"})
    assert response.status_code == 200
    assert len(response.json()) == 0

    # Check DB
    session.refresh(db_key)
    assert db_key.status == "revoked"
    assert db_key.revoked_at is not None
