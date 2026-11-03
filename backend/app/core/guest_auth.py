import hashlib

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.sessions import SessionParticipant, TableSession
from app.models.entities import Restaurant

guest_bearer = HTTPBearer(auto_error=False)


def get_current_guest(
    credentials: HTTPAuthorizationCredentials | None = Depends(guest_bearer),
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Guest token required")

    token_hash = hashlib.sha256(
        credentials.credentials.encode("utf-8")
    ).hexdigest()

    participant = db.scalar(
        select(SessionParticipant).where(
            SessionParticipant.guest_token_hash == token_hash,
            SessionParticipant.status == "active",
        )
    )

    if participant is None:
        raise HTTPException(status_code=401, detail="Invalid guest token")

    session = db.scalar(
        select(TableSession).where(
            TableSession.id == participant.session_id,
            TableSession.restaurant_id == participant.restaurant_id,
            TableSession.status == "active",
        )
    )

    if session is None:
        raise HTTPException(status_code=403, detail="Table session is not active")

    restaurant = db.scalar(
        select(Restaurant).where(
            Restaurant.id == participant.restaurant_id,
            Restaurant.is_active.is_(True),
        )
    )
    if restaurant is None:
        raise HTTPException(status_code=403, detail="Restaurant is unavailable")

    return participant
