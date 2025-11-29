from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from orbit.core.config import settings
from orbit.api.v1.api import api_router
from orbit.db.session import engine
from orbit.models.workflow import SQLModel

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to DB, etc.
    print("Orbit System Initializing...")
    # Create tables for SQLite (for dev convenience)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    # Shutdown: Close connections
    print("Orbit System Shutting Down...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.API_V1_STR)


# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/")
async def root():
    return {
        "message": "Welcome to Orbit",
        "status": "operational",
        "version": "0.1.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}
