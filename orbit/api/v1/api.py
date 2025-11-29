from fastapi import APIRouter
from orbit.api.v1.endpoints import workflows

api_router = APIRouter()
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
