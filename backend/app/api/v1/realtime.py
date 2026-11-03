import hashlib
import uuid

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import JWT_SECRET_KEY, JWT_ALGORITHM
from app.models.entities import User, Restaurant
from app.models.sessions import TableSession, SessionParticipant
from app.websocket.manager import manager

router = APIRouter(tags=["Real-time Updates"])

@router.websocket("/ws/customer/{session_id}")
async def customer_websocket(websocket: WebSocket, session_id: uuid.UUID):
    token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=1008, reason="Guest token required")
        return

    db = SessionLocal()

    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        participant = db.scalar(
            select(SessionParticipant).where(
                SessionParticipant.guest_token_hash == token_hash,
                SessionParticipant.session_id == session_id,
                SessionParticipant.status == "active",
            )
        )

        if participant is None:
            await websocket.close(code=1008, reason="Invalid guest token")
            return

        session = db.scalar(
            select(TableSession).where(
                TableSession.id == session_id,
                TableSession.restaurant_id == participant.restaurant_id,
                TableSession.status == "active",
            )
        )

        restaurant = db.scalar(
            select(Restaurant).where(
                Restaurant.id == participant.restaurant_id,
                Restaurant.is_active.is_(True),
            )
        )

        if restaurant is None:
            await websocket.close(code=1008, reason="Restaurant unavailable")
            return
        if session is None:
            await websocket.close(code=1008, reason="Inactive table session")
            return

        await manager.connect_customer(str(session_id), websocket)

        await websocket.send_json({
            "event": "connected",
            "session_id": str(session_id),
            "message": "Connected to TableFlow updates",
        })

        while True:
            # Keep connection alive. Clients may send ping messages.
            message = await websocket.receive_text()

            if message == "ping":
                await websocket.send_json({"event": "pong"})

    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect_customer(str(session_id), websocket)
        db.close()


@router.websocket("/ws/staff")
async def staff_websocket(websocket: WebSocket):
    token = websocket.query_params.get("token")

    if not token or not JWT_SECRET_KEY:
        await websocket.close(code=1008, reason="Authentication required")
        return

    db = SessionLocal()
    restaurant_id = None

    try:
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[JWT_ALGORITHM],
            )
            user_id = uuid.UUID(payload.get("sub", ""))
        except (jwt.InvalidTokenError, ValueError, TypeError):
            await websocket.close(code=1008, reason="Invalid access token")
            return

        user = db.scalar(
            select(User).where(
                User.id == user_id,
                User.is_active.is_(True),
            )
        )

        if (
            user is None
            or user.restaurant_id is None
            or user.role not in {"owner", "admin", "manager", "staff", "kitchen"}
            or payload.get("role") != user.role
            or payload.get("restaurant_id") != str(user.restaurant_id)
        ):
            await websocket.close(code=1008, reason="Access denied")
            return

        restaurant = db.scalar(
            select(Restaurant).where(
                Restaurant.id == user.restaurant_id,
                Restaurant.is_active.is_(True),
            )
        )
        if restaurant is None:
            await websocket.close(code=1008, reason="Restaurant unavailable")
            return
        restaurant_id = str(user.restaurant_id)

        await manager.connect_staff(restaurant_id, websocket)

        await websocket.send_json({
            "event": "connected",
            "restaurant_id": restaurant_id,
            "message": "Connected to restaurant updates",
        })

        while True:
            message = await websocket.receive_text()

            if message == "ping":
                await websocket.send_json({"event": "pong"})

    except WebSocketDisconnect:
        pass
    finally:
        if restaurant_id:
            await manager.disconnect_staff(restaurant_id, websocket)
        db.close()
