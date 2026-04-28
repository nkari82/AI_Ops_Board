from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from websocket_manager import manager

class BroadcastRequest(BaseModel):
    message: str

router = APIRouter(prefix="/ws", tags=["websocket"])

@router.websocket("/status")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@router.post("/broadcast")
async def broadcast_message(request: BroadcastRequest):
    await manager.broadcast(request.message)
    return {"message": "Broadcast successful"}
