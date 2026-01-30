from fastapi import APIRouter, Depends
from typing import Dict, Any
from app.auth import get_current_user

router = APIRouter(tags=["users"])

@router.get("/me")
async def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {
        "user_id": current_user.get("user_id"),
        "max_budget": current_user.get("max_budget"),
        "spend": current_user.get("spend", 0.0)
    }
