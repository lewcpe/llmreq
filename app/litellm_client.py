import httpx
from app.config import settings
from typing import Optional, Dict, Any, List

class LiteLLMClient:
    def __init__(self):
        self.base_url = settings.LITELLM_API_URL
        self.master_key = settings.LITELLM_MASTER_KEY
        self.headers = {"Authorization": f"Bearer {self.master_key}"}

    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/user/info/{user_id}",
                    headers=self.headers
                )
                if response.status_code == 200:
                    return response.json()
                if response.status_code == 404: # Assuming 404 if user not found, strictly speaking checking API behavior is good.
                    # LiteLLM might return empty or error.
                    return None
                # If other error, maybe raise?
                return None
            except httpx.RequestError:
                raise Exception("LiteLLM Service Unavailable")

    async def create_user(self, user_id: str, user_email: str, max_budget: Optional[float] = None) -> Dict[str, Any]:
        payload = {
            "user_id": user_id,
            "user_email": user_email
        }
        if max_budget is not None:
            payload["max_budget"] = max_budget

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/user/new",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.RequestError:
                 raise Exception("LiteLLM Service Unavailable")

    async def list_keys(self, user_id: str) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/key/list",
                    params={"user_id": user_id},
                    headers=self.headers
                )
                if response.status_code == 200:
                    return response.json().get("keys", [])
                return []
            except httpx.RequestError:
                 raise Exception("LiteLLM Service Unavailable")

    async def generate_key(self, user_id: str, key_alias: str, max_budget: Optional[float] = None, duration: Optional[str] = None) -> Dict[str, Any]:
        payload = {
            "user_id": user_id,
            "key_alias": key_alias,
        }
        if max_budget is not None:
            payload["max_budget"] = max_budget
        if duration is not None:
            payload["duration"] = duration

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/key/generate",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
            except httpx.RequestError:
                 raise Exception("LiteLLM Service Unavailable")

    async def delete_key(self, key: str) -> bool:
        payload = {"keys": [key]}
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/key/delete",
                    json=payload,
                    headers=self.headers
                )
                return response.status_code == 200
            except httpx.RequestError:
                 raise Exception("LiteLLM Service Unavailable")

litellm_client = LiteLLMClient()
