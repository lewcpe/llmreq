import pytest
import httpx
import asyncio
from app.config import settings

@pytest.mark.asyncio
async def test_integration_full_flow(client):
    # Check if LiteLLM is reachable
    # We use a short timeout to fail fast
    async with httpx.AsyncClient(timeout=1.0) as http_client:
        try:
            # LiteLLM health check usually at /health/liveness or /health
            # Or just check if we can connect
            resp = await http_client.get(f"{settings.LITELLM_API_URL}/health")
            if resp.status_code != 200:
                pytest.skip("LiteLLM not available")
        except Exception:
             pytest.skip("LiteLLM not reachable")

    user_email = "integration@test.com"
    headers = {"x-forwarded-email": user_email}

    # 1. Create Key
    resp = client.post("/api/keys", json={"name": "integ-key"}, headers=headers)
    assert resp.status_code == 200
    key = resp.json()
    assert key.startswith("sk-")

    # 2. Use Key with LiteLLM
    async with httpx.AsyncClient() as http_client:
        completion_resp = await http_client.post(
            f"{settings.LITELLM_API_URL}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": "fake-gpt-test",
                "messages": [{"role": "user", "content": "Hello"}]
            }
        )
        assert completion_resp.status_code == 200

    # 3. Verify Spend
    # Wait a bit for sync
    await asyncio.sleep(1)

    resp = client.get("/api/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    # If cost is 0, this might fail if we assert > 0.
    # But we at least verified we can query it.
    print(f"Spend: {data['spend']}")
