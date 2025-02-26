from typing import Dict, Set, Optional, Any, Protocol
from datetime import datetime
from uuid import UUID
import asyncio
from fastapi import Depends
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from app.models.models import Notification

class NotificationModel(Protocol):
    id: UUID
    user_id: UUID
    opportunity_id: Optional[UUID]
    type: str
    message: str
    read: bool
    created_at: datetime

class DatabaseSession(Protocol):
    def query(self, *entities: Any, **kwargs: Any) -> Any: ...
    def add(self, instance: Any) -> None: ...
    def commit(self) -> None: ...
    def close(self) -> None: ...

class WebSocketConnection(Protocol):
    async def accept(self) -> None: ...
    async def send_json(self, data: Dict[str, Any]) -> None: ...
    async def receive_json(self) -> Dict[str, Any]: ...
    async def close(self) -> None: ...

class NotificationManager:
    def __init__(self) -> None:
        self.active_connections: Dict[UUID, Set[WebSocketConnection]] = {}
        self._background_tasks: Set[asyncio.Task[Any]] = set()

    async def connect(self, user_id: UUID, websocket: WebSocketConnection) -> None:
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    async def disconnect(self, user_id: UUID, websocket: WebSocketConnection) -> None:
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_notification(self, user_id: UUID, notification_data: Dict[str, Any]) -> None:
        if user_id in self.active_connections:
            dead_connections: Set[WebSocketConnection] = set()
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(notification_data)
                except Exception:
                    dead_connections.add(connection)
            
            for dead_connection in dead_connections:
                self.active_connections[user_id].remove(dead_connection)

    async def broadcast(self, notification_data: Dict[str, Any]) -> None:
        for user_id in self.active_connections:
            await self.send_notification(user_id, notification_data)

notification_manager = NotificationManager()

async def handle_notification_event(
    user_id: UUID,
    opportunity_id: Optional[UUID],
    notification_type: str,
    message: str,
    db: DatabaseSession
) -> None:
    notification = Notification(
        user_id=user_id,
        opportunity_id=opportunity_id,
        type=notification_type,
        message=message,
        read=False,
        created_at=datetime.now(ZoneInfo("UTC"))
    )
    
    db.add(notification)
    db.commit()
    
    notification_data: Dict[str, Any] = {
        "id": str(notification.id),
        "type": notification_type,
        "message": message,
        "created_at": notification.created_at.isoformat()
    }
    
    await notification_manager.send_notification(user_id, notification_data)

async def mark_notification_read(
    notification_id: UUID,
    user_id: UUID,
    db: DatabaseSession
) -> bool:
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id
    ).first()
    
    if notification:
        notification.read = True
        db.commit()
        return True
    return False

async def notification_websocket_endpoint(
    websocket: WebSocketConnection,
    user_id: UUID,
    db: Session = Depends()
) -> None:
    await websocket.accept()
    await notification_manager.connect(user_id, websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("action") == "mark_read":
                notification_id = UUID(data["notification_id"])
                success = await mark_notification_read(notification_id, user_id, db)
                await websocket.send_json({"success": success})
    except Exception:
        pass
    finally:
        await notification_manager.disconnect(user_id, websocket)
        await websocket.close() 