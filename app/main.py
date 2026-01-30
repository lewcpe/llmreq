from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import create_db_and_tables
from app.config import settings
from app.routers import users, keys

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan, title="LiteLLM Request Manager")

app.include_router(users.router, prefix=settings.LLMREQ_PREFIX)
app.include_router(keys.router, prefix=settings.LLMREQ_PREFIX)

@app.get("/health")
def health():
    return {"status": "ok"}
