from fastapi import Header, HTTPException
from typing import Annotated, Dict, Any
from app.litellm_client import litellm_client
from app.config import settings

async def get_current_user(x_forwarded_email: Annotated[str | None, Header()] = None) -> Dict[str, Any]:
    if not x_forwarded_email:
        raise HTTPException(status_code=401, detail="Missing X-Forwarded-Email header")

    user_email = x_forwarded_email.lower()
    user_id = user_email

    try:
        user_info = await litellm_client.get_user_info(user_id)
        if not user_info:
            # Create user
            await litellm_client.create_user(
                user_id=user_id,
                user_email=user_email,
                max_budget=settings.LLMREQ_DEFAULT_BUDGET
            )
            # Fetch again or construct object
            user_info = await litellm_client.get_user_info(user_id)
            if not user_info:
                 user_info = {
                     "user_id": user_id,
                     "user_email": user_email,
                     "max_budget": settings.LLMREQ_DEFAULT_BUDGET,
                     "spend": 0.0
                 }
    except Exception as e:
        if "LiteLLM Service Unavailable" in str(e):
             raise HTTPException(status_code=503, detail="LiteLLM Service Unavailable")
        # Log error
        print(f"Error in JIT provisioning: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error during Authentication")

    return user_info
