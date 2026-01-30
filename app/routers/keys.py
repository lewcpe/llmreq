from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Dict, Any
from app.auth import get_current_user
from app.database import get_session
from app.models import KeyHistory
from app.schemas import CreateKeyRequest, KeyResponse
from app.litellm_client import litellm_client
from app.config import settings
from datetime import datetime

router = APIRouter(prefix="/keys", tags=["keys"])

def mask_key(key: str) -> str:
    if not key:
        return "masked"
    if len(key) <= 8:
        return "..."
    return key[:4] + "..." + key[-4:]

@router.get("/active", response_model=List[KeyResponse])
async def get_active_keys(
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    user_id = current_user["user_id"]

    try:
        litellm_keys = await litellm_client.list_keys(user_id)
    except Exception:
        raise HTTPException(status_code=503, detail="LiteLLM Service Unavailable")

    active_keys_response = []
    active_aliases = set()

    for l_key in litellm_keys:
        alias = l_key.get("key_alias")
        if not alias:
            continue

        active_aliases.add(alias)

        stmt = select(KeyHistory).where(KeyHistory.user_id == user_id, KeyHistory.key_name == alias)
        db_key = session.exec(stmt).first()

        if not db_key:
            token = l_key.get("token", "")
            db_key = KeyHistory(
                user_id=user_id,
                litellm_key_id=token,
                key_name=alias,
                key_mask=mask_key(token),
                key_type="standard",
                status="active"
            )
            session.add(db_key)
            session.commit()
            session.refresh(db_key)

        if db_key.status != "active":
             db_key.status = "active"
             db_key.revoked_at = None
             session.add(db_key)
             session.commit()

        active_keys_response.append(KeyResponse(
            key_name=db_key.key_name,
            key_mask=db_key.key_mask,
            created_at=db_key.created_at,
            spend=l_key.get("spend", 0.0),
            type=db_key.key_type,
            status="active"
        ))

    # Sync: Check for zombies (active in DB but not in LiteLLM)
    stmt = select(KeyHistory).where(KeyHistory.user_id == user_id, KeyHistory.status == "active")
    db_active_keys = session.exec(stmt).all()

    commits_needed = False
    for db_k in db_active_keys:
        if db_k.key_name not in active_aliases:
            db_k.status = "revoked"
            db_k.revoked_at = datetime.now()
            session.add(db_k)
            commits_needed = True

    if commits_needed:
        session.commit()

    return active_keys_response

@router.get("/history", response_model=List[KeyResponse])
async def get_key_history(
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    user_id = current_user["user_id"]
    stmt = select(KeyHistory).where(
        KeyHistory.user_id == user_id,
        (KeyHistory.status == "revoked") | (KeyHistory.revoked_at != None)
    )
    history = session.exec(stmt).all()

    return [
        KeyResponse(
            key_name=k.key_name,
            key_mask=k.key_mask,
            created_at=k.created_at,
            spend=0.0,
            type=k.key_type,
            status="revoked"
        ) for k in history
    ]

@router.post("", response_model=str)
async def create_key(
    request: CreateKeyRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    user_id = current_user["user_id"]

    try:
        litellm_keys = await litellm_client.list_keys(user_id)
    except Exception:
        raise HTTPException(status_code=503, detail="LiteLLM Service Unavailable")

    if len(litellm_keys) >= settings.LLMREQ_MAX_ACTIVE_KEY:
        raise HTTPException(status_code=400, detail="Max active keys limit reached")

    if request.type == "long-term":
        long_term_count = 0
        for l_key in litellm_keys:
            alias = l_key.get("key_alias")
            if alias:
                stmt = select(KeyHistory).where(KeyHistory.user_id == user_id, KeyHistory.key_name == alias)
                db_key = session.exec(stmt).first()
                if db_key and db_key.key_type == "long-term":
                    long_term_count += 1

        if long_term_count >= settings.LLMREQ_LONGTERM_KEY_LIMIT:
             raise HTTPException(status_code=400, detail="Max long-term keys limit reached")

    duration = None
    budget = request.budget

    if request.type == "long-term":
        duration = settings.LLMREQ_LONGTERM_KEY_LIFETIME
        budget = settings.LLMREQ_LONGTERM_KEY_BUDGET
    else:
        if budget is None:
            budget = settings.LLMREQ_DEFAULT_BUDGET

    try:
        response = await litellm_client.generate_key(
            user_id=user_id,
            key_alias=request.name,
            max_budget=budget,
            duration=duration
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    raw_key = response.get("key")
    token = response.get("token", "unknown")

    db_key = KeyHistory(
        user_id=user_id,
        litellm_key_id=token,
        key_name=request.name,
        key_mask=mask_key(raw_key),
        key_type=request.type,
        status="active"
    )
    session.add(db_key)
    session.commit()

    return raw_key

@router.delete("/{key_name}")
async def delete_key(
    key_name: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    user_id = current_user["user_id"]

    stmt = select(KeyHistory).where(KeyHistory.user_id == user_id, KeyHistory.key_name == key_name, KeyHistory.status == "active")
    db_key = session.exec(stmt).first()

    if not db_key:
        raise HTTPException(status_code=404, detail="Key not found")

    success = await litellm_client.delete_key(key_name)

    if not success:
         raise HTTPException(status_code=500, detail="Failed to delete key in LiteLLM")

    db_key.status = "revoked"
    db_key.revoked_at = datetime.now()
    session.add(db_key)
    session.commit()

    return {"status": "ok"}
