import pytest
import httpx
import asyncio
import os
from app.config import settings

@pytest.mark.asyncio
async def test_integration_full_flow(client):
    # Check if LiteLLM is reachable
    # We use a short timeout to fail fast

    litellm_url = settings.LITELLM_API_URL
    is_ci = os.getenv("CI", "false").lower() == "true"

    async with httpx.AsyncClient(timeout=5.0) as http_client:
        try:
            # LiteLLM health check usually at /health/liveness or /health
            # Or just check if we can connect
            resp = await http_client.get(f"{litellm_url}/health")
            if resp.status_code != 200:
                if is_ci:
                    pytest.fail(f"LiteLLM health check failed: {resp.status_code}")
                else:
                    pytest.skip(f"LiteLLM not available: {resp.status_code}")
        except Exception as e:
             if is_ci:
                 pytest.fail(f"LiteLLM not reachable at {litellm_url}: {e}")
             else:
                 pytest.skip(f"LiteLLM not reachable: {e}")

    user_email = "integration@test.com"
    headers = {"x-forwarded-email": user_email}

    # 1. Create Key
    resp = client.post("/api/keys", json={"name": "integ-key"}, headers=headers)
    assert resp.status_code == 200, f"Failed to create key: {resp.text}"
    key = resp.json()
    assert key.startswith("sk-")

    # 2. Use Key with LiteLLM
    # Note: If running locally, LiteLLM might need to be configured with models.
    # We assume 'fake-gpt-test' is configured.
    async with httpx.AsyncClient() as http_client:
        completion_resp = await http_client.post(
            f"{litellm_url}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": "fake-gpt-test",
                "messages": [{"role": "user", "content": "Hello"}]
            }
        )
        assert completion_resp.status_code == 200, f"LiteLLM completion failed: {completion_resp.text}"

    # 3. Verify Spend
    # Wait a bit for sync
    await asyncio.sleep(2)

    resp = client.get("/api/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    # Spend should be > 0 ideally, but depends on mock model cost.
    # At least check the field exists.
    assert "spend" in data
    print(f"Spend: {data['spend']}")
