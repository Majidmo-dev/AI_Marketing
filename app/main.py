from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.db.session import engine
from app.models.entities import Base
from app.api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_tables and settings.environment == "local":
        async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.include_router(router, prefix=settings.api_v1_prefix)

@app.get("/health")
async def health(): return {"status": "ok", "environment": settings.environment}
