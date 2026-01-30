from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel

class KeyHistory(SQLModel, table=True):
    __tablename__ = "key_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    litellm_key_id: str
    key_name: str
    key_mask: str
    key_type: str = Field(default="standard")
    created_at: datetime = Field(default_factory=datetime.now)
    revoked_at: Optional[datetime] = None
    status: str = "active"
