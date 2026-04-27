from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from websocket_manager import manager

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
async def broadcast_message(message: str):
    await manager.broadcast(message)
    return {"message": "Broadcast successful"}
