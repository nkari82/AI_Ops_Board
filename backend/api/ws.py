from importlib import import_module

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel


def _load_manager():
    try:
        module = import_module("backend.websocket_manager")
    except ModuleNotFoundError:
        module = import_module("websocket_manager")
    return module.manager


manager = _load_manager()

class BroadcastRequest(BaseModel):
    message: str

router = APIRouter(prefix="/ws", tags=["websocket"])

@router.websocket("/status")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@router.post("/broadcast")
async def broadcast_message(request: BroadcastRequest):
    await manager.broadcast(request.message)
    return {"message": "Broadcast successful"}
