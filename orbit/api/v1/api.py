from fastapi import APIRouter

from orbit.api.v1.endpoints import websocket, workflows

api_router = APIRouter()
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(websocket.router, tags=["websocket"])
