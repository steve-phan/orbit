from fastapi import APIRouter

from orbit.api.v1.endpoints import workflows, websocket, schedules, metrics

api_router = APIRouter()
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(schedules.router, prefix="/workflows", tags=["schedules"])
api_router.include_router(websocket.router, tags=["websocket"])
api_router.include_router(metrics.router, tags=["metrics"])
