import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.core.guest_auth import get_current_guest
from app.models.entities import User
from app.models.sessions import TableSession, SessionParticipant
from app.models.service_requests import ServiceRequest
from app.websocket.manager import manager

router = APIRouter(tags=["Service Requests"])

STAFF_ROLES = ("owner", "admin", "manager", "staff")
REQUEST_TYPES = {"waiter", "water", "bill", "assistance", "other"}

TRANSITIONS = {
    "pending": {"acknowledged", "cancelled"},
    "acknowledged": {"in_progress", "resolved", "cancelled"},
    "in_progress": {"resolved", "cancelled"},
    "resolved": set(),
    "cancelled": set(),
}


class ServiceRequestCreate(BaseModel):
    request_type: str
    message: str | None = Field(default=None, max_length=500)


class ServiceRequestUpdate(BaseModel):
    status: str


def serialize_request(request: ServiceRequest):
    return {
        "id": str(request.id),
        "restaurant_id": str(request.restaurant_id),
        "session_id": str(request.session_id),
        "participant_id": (
            str(request.participant_id) if request.participant_id else None
        ),
        "request_type": request.request_type,
        "message": request.message,
        "status": request.status,
        "assigned_to": (
            str(request.assigned_to) if request.assigned_to else None
        ),
        "created_at": (
            request.created_at.isoformat() if request.created_at else None
        ),
        "resolved_at": (
            request.resolved_at.isoformat() if request.resolved_at else None
        ),
    }


@router.post("/api/v1/customer/service-requests", status_code=201)
async def create_service_request(
    data: ServiceRequestCreate,
    participant: SessionParticipant = Depends(get_current_guest),
    db: Session = Depends(get_db),
):
    request_type = data.request_type.strip().lower()

    if request_type not in REQUEST_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported request type")

    request = ServiceRequest(
        restaurant_id=participant.restaurant_id,
        session_id=participant.session_id,
        participant_id=participant.id,
        request_type=request_type,
        message=data.message.strip() if data.message else None,
        status="pending",
    )

    db.add(request)
    db.commit()
    db.refresh(request)

    result = serialize_request(request)

    await manager.broadcast_table_event(
        str(request.restaurant_id),
        str(request.session_id),
        {"event": "service_request_created", "request": result},
    )

    return result


@router.get("/api/v1/customer/service-requests")
def get_customer_service_requests(
    participant: SessionParticipant = Depends(get_current_guest),
    db: Session = Depends(get_db),
):
    requests = db.scalars(
        select(ServiceRequest)
        .where(
            ServiceRequest.session_id == participant.session_id,
            ServiceRequest.restaurant_id == participant.restaurant_id,
        )
        .order_by(ServiceRequest.created_at.desc())
    ).all()

    return [serialize_request(item) for item in requests]


@router.get("/api/v1/staff/service-requests")
def get_staff_service_requests(
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    if user.restaurant_id is None:
        raise HTTPException(status_code=403, detail="Restaurant access required")

    query = select(ServiceRequest).where(
        ServiceRequest.restaurant_id == user.restaurant_id
    )

    if status:
        if status not in {
            "pending", "acknowledged", "in_progress", "resolved", "cancelled"
        }:
            raise HTTPException(status_code=422, detail="Invalid status filter")
        query = query.where(ServiceRequest.status == status)

    requests = db.scalars(
        query.order_by(ServiceRequest.created_at.desc())
    ).all()

    return [serialize_request(item) for item in requests]


@router.patch("/api/v1/staff/service-requests/{request_id}")
async def update_service_request(
    request_id: uuid.UUID,
    data: ServiceRequestUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    if user.restaurant_id is None:
        raise HTTPException(status_code=403, detail="Restaurant access required")

    request = db.scalar(
        select(ServiceRequest)
        .where(
            ServiceRequest.id == request_id,
            ServiceRequest.restaurant_id == user.restaurant_id,
        )
        .with_for_update()
    )

    if request is None:
        raise HTTPException(status_code=404, detail="Request not found")

    new_status = data.status.strip().lower()

    if new_status not in TRANSITIONS.get(request.status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change request from {request.status} to {new_status}",
        )

    request.status = new_status
    request.assigned_to = user.id if new_status != "cancelled" else None

    if new_status == "resolved":
        request.resolved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(request)

    result = serialize_request(request)

    await manager.broadcast_table_event(
        str(request.restaurant_id),
        str(request.session_id),
        {"event": "service_request_updated", "request": result},
    )

    return result
