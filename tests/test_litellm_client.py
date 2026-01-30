import pytest
from unittest.mock import MagicMock, patch
from app.litellm_client import LiteLLMClient
from app.config import settings

@pytest.mark.asyncio
async def test_get_user_info_success():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"user_id": "u1"})

        client = LiteLLMClient()
        result = await client.get_user_info("u1")
        assert result["user_id"] == "u1"
        mock_get.assert_called_with(
            f"{settings.LITELLM_API_URL}/user/info/u1",
            headers={"Authorization": f"Bearer {settings.LITELLM_MASTER_KEY}"}
        )

@pytest.mark.asyncio
async def test_get_user_info_404():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=404)

        client = LiteLLMClient()
        result = await client.get_user_info("u1")
        assert result is None

@pytest.mark.asyncio
async def test_create_user_success():
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {"status": "ok"})

        client = LiteLLMClient()
        result = await client.create_user("u1", "e1")
        assert result["status"] == "ok"

@pytest.mark.asyncio
async def test_list_keys_success():
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"keys": [{"token": "k1"}]})

        client = LiteLLMClient()
        result = await client.list_keys("u1")
        assert len(result) == 1
        assert result[0]["token"] == "k1"

@pytest.mark.asyncio
async def test_generate_key_success():
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {"key": "sk-1"})

        client = LiteLLMClient()
        result = await client.generate_key("u1", "alias")
        assert result["key"] == "sk-1"

@pytest.mark.asyncio
async def test_delete_key_success():
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)

        client = LiteLLMClient()
        result = await client.delete_key("k1")
        assert result is True
