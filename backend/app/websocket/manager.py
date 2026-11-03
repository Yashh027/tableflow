import asyncio
from collections import defaultdict
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.restaurant_connections = defaultdict(set)
        self.session_connections = defaultdict(set)
        self.lock = asyncio.Lock()

    async def connect_staff(self, restaurant_id: str, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.restaurant_connections[restaurant_id].add(websocket)

    async def connect_customer(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.session_connections[session_id].add(websocket)

    async def disconnect_staff(self, restaurant_id: str, websocket: WebSocket):
        async with self.lock:
            self.restaurant_connections[restaurant_id].discard(websocket)

    async def disconnect_customer(self, session_id: str, websocket: WebSocket):
        async with self.lock:
            self.session_connections[session_id].discard(websocket)

    async def broadcast_staff(self, restaurant_id: str, event: dict):
        async with self.lock:
            connections = list(self.restaurant_connections.get(restaurant_id, set()))

        disconnected = []
        for connection in connections:
            try:
                await connection.send_json(event)
            except Exception:
                disconnected.append(connection)

        for connection in disconnected:
            await self.disconnect_staff(restaurant_id, connection)

    async def broadcast_session(self, session_id: str, event: dict):
        async with self.lock:
            connections = list(self.session_connections.get(session_id, set()))

        disconnected = []
        for connection in connections:
            try:
                await connection.send_json(event)
            except Exception:
                disconnected.append(connection)

        for connection in disconnected:
            await self.disconnect_customer(session_id, connection)

    async def broadcast_table_event(
        self,
        restaurant_id: str,
        session_id: str,
        event: dict,
    ):
        await asyncio.gather(
            self.broadcast_staff(restaurant_id, event),
            self.broadcast_session(session_id, event),
        )


manager = ConnectionManager()
