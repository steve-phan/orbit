from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from orbit.services.websocket_manager import ws_manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time workflow and task updates.
    Clients connect here to receive live execution status.
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for client messages
            await websocket.receive_text()
            # Echo back for heartbeat
            await ws_manager.send_personal_message(
                {"type": "heartbeat", "message": "connected"}, websocket
            )
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
