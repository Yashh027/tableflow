import hashlib
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.entities import User, DiningTable, Restaurant
from app.models.sessions import TableSession, SessionParticipant

router = APIRouter(tags=["Tables and Customer Sessions"])


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def require_restaurant(user: User):
    if user.restaurant_id is None:
        raise HTTPException(status_code=403, detail="Restaurant access required")
    return user.restaurant_id


class TableCreate(BaseModel):
    table_number: str = Field(min_length=1, max_length=30)
    capacity: int = Field(default=4, ge=1, le=30)


class GuestJoinRequest(BaseModel):
    qr_token: str = Field(min_length=20, max_length=200)
    guest_name: str = Field(min_length=1, max_length=100)


@router.post(
    "/tables",
    status_code=status.HTTP_201_CREATED,
)
def create_table(
    data: TableCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("owner", "admin", "manager")),
):
    restaurant_id = require_restaurant(user)

    raw_qr_token = secrets.token_urlsafe(32)

    table = DiningTable(
        restaurant_id=restaurant_id,
        table_number=data.table_number.strip(),
        capacity=data.capacity,
        qr_token_hash=hash_token(raw_qr_token),
    )

    db.add(table)

    try:
        db.commit()
        db.refresh(table)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Table number already exists",
        )

    return {
        "message": "Table created",
        "table_id": str(table.id),
        "table_number": table.table_number,
        "capacity": table.capacity,
        "qr_token": raw_qr_token,
        "warning": "Save this QR token securely. It will not be returned again.",
    }


@router.post(
    "/customer/sessions/join",
    status_code=status.HTTP_201_CREATED,
)
def join_table_session(
    data: GuestJoinRequest,
    db: Session = Depends(get_db),
):
    qr_hash = hash_token(data.qr_token)

    # Lock the table row to serialize session creation for this table.
    table = db.scalar(
        select(DiningTable)
        .where(
            DiningTable.qr_token_hash == qr_hash,
            DiningTable.is_active.is_(True),
        )
        .with_for_update()
    )

    if table is None:
        raise HTTPException(status_code=404, detail="Invalid table QR code")

    restaurant = db.scalar(
        select(Restaurant).where(
            Restaurant.id == table.restaurant_id,
            Restaurant.is_active.is_(True),
        )
    )
    if restaurant is None:
        raise HTTPException(status_code=403, detail="Restaurant is unavailable")
    if not data.guest_name.strip():
        raise HTTPException(status_code=422, detail="Guest name is required")

    session = db.scalar(
        select(TableSession).where(
            TableSession.table_id == table.id,
            TableSession.restaurant_id == table.restaurant_id,
            TableSession.status == "active",
        )
    )

    if session is None:
        session = TableSession(
            restaurant_id=table.restaurant_id,
            table_id=table.id,
            status="active",
        )
        db.add(session)
        db.flush()

    raw_guest_token = secrets.token_urlsafe(32)

    participant = SessionParticipant(
        restaurant_id=table.restaurant_id,
        session_id=session.id,
        guest_name=data.guest_name.strip(),
        guest_token_hash=hash_token(raw_guest_token),
        status="active",
    )

    db.add(participant)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not join table session. Please retry.",
        )

    return {
        "message": "Successfully joined table session",
        "session_id": str(session.id),
        "participant_id": str(participant.id),
        "restaurant_id": str(table.restaurant_id),
        "table_number": table.table_number,
        "guest_name": participant.guest_name,
        "guest_token": raw_guest_token,
        "session_status": session.status,
    }
