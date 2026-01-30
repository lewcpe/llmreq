from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    LLMREQ_PREFIX: str = "/api"
    LITELLM_API_URL: str = "http://litellm:4000"
    LITELLM_MASTER_KEY: str = Field(..., description="Master key for LiteLLM")
    LLMREQ_DATABASE_URL: str = "sqlite:///./app.db"
    LLMREQ_DEFAULT_BUDGET: float = 1.0
    LLMREQ_LONGTERM_KEY_LIFETIME: str = "400d"
    LLMREQ_LONGTERM_KEY_LIMIT: int = 1
    LLMREQ_LONGTERM_KEY_BUDGET: float = 20.0
    LLMREQ_MAX_ACTIVE_KEY: int = 10

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
