import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ServiceRequest(Base):
    __tablename__ = "service_requests"
    __table_args__ = (
        CheckConstraint(
            "request_type IN ('waiter', 'water', 'bill', 'assistance', 'other')",
            name="ck_service_request_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'acknowledged', 'in_progress', 'resolved', 'cancelled')",
            name="ck_service_request_status",
        ),
        ForeignKeyConstraint(
            ["participant_id", "session_id", "restaurant_id"],
            [
                "session_participants.id",
                "session_participants.session_id",
                "session_participants.restaurant_id",
            ],
            name="fk_service_request_participant_session_restaurant",
        ),
        ForeignKeyConstraint(
            ["session_id", "restaurant_id"],
            ["table_sessions.id", "table_sessions.restaurant_id"],
            name="fk_service_request_session_restaurant",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("table_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    participant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("session_participants.id", ondelete="SET NULL"),
        nullable=True,
    )
    request_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
