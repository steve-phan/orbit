from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.exceptions import HTTPException as StarletteHTTPException

from orbit.api.v1.api import api_router
from orbit.core.config import settings
from orbit.core.exception_handlers import (
    http_exception_handler,
    orbit_exception_handler,
    validation_exception_handler,
)
from orbit.core.exceptions import OrbitException
from orbit.core.logging import get_logger, setup_logging
from orbit.core.rate_limit import RateLimitMiddleware
from orbit.db.session import engine
from orbit.models.workflow import SQLModel
from orbit.services.scheduler import scheduler

# Initialize logging
setup_logging()
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to DB, etc.
    logger.info("Orbit System Initializing...")
    # Create tables for SQLite (for dev convenience)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    logger.info("Database tables created")

    # Start scheduler
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await scheduler.start(async_session)
    logger.info("Workflow scheduler started")

    yield

    # Shutdown: Close connections
    await scheduler.stop()
    logger.info("Workflow scheduler stopped")
    logger.info("Orbit System Shutting Down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Register exception handlers
app.add_exception_handler(OrbitException, orbit_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)

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

# Add rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=100,  # 100 requests per minute
    burst_size=150,  # Allow bursts up to 150
    exclude_paths=["/health", "/api/v1/metrics", "/api/v1/ws"],
)


@app.get("/")
async def root():
    return {
        "message": "Welcome to Orbit",
        "status": "operational",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}
