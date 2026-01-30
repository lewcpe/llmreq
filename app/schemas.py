from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class CreateKeyRequest(BaseModel):
    name: str = Field(..., description="User provided alias")
    budget: Optional[float] = Field(None, description="Optional budget cap")
    type: Literal["standard", "long-term"] = "standard"

class KeyResponse(BaseModel):
    key_name: str
    key_mask: str
    created_at: datetime
    spend: float = 0.0
    type: str
    status: str
