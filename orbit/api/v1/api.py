from fastapi import APIRouter

from orbit.api.v1.endpoints import (
    auth,
    history,
    metrics,
    schedules,
    templates,
    variables,
    versioning,
    websocket,
    workflows,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(schedules.router, prefix="/workflows", tags=["schedules"])
api_router.include_router(variables.router, prefix="/workflows", tags=["variables"])
api_router.include_router(versioning.router, prefix="/workflows", tags=["versioning"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(history.router, tags=["history"])
api_router.include_router(websocket.router, tags=["websocket"])
api_router.include_router(metrics.router, tags=["metrics"])
