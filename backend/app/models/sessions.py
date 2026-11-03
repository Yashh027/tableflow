import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TableSession(Base):
    __tablename__ = "table_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'closing', 'closed')",
            name="ck_table_session_status",
        ),
        UniqueConstraint("id", "restaurant_id", name="uq_table_session_id_restaurant"),
        ForeignKeyConstraint(
            ["table_id", "restaurant_id"],
            ["dining_tables.id", "dining_tables.restaurant_id"],
            name="fk_table_session_table_restaurant",
        ),
        Index(
            "uq_active_session_per_table",
            "table_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
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
    table_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("dining_tables.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class SessionParticipant(Base):
    __tablename__ = "session_participants"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'left')",
            name="ck_participant_status",
        ),
        UniqueConstraint("id", "restaurant_id", name="uq_participant_id_restaurant"),
        UniqueConstraint("id", "session_id", "restaurant_id", name="uq_participant_id_session_restaurant"),
        ForeignKeyConstraint(
            ["session_id", "restaurant_id"],
            ["table_sessions.id", "table_sessions.restaurant_id"],
            name="fk_participant_session_restaurant",
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
    guest_name: Mapped[str] = mapped_column(String(100), nullable=False)
    guest_token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    left_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
