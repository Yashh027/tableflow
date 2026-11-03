import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CustomerOrder(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'accepted', 'preparing', 'ready', 'served', 'completed', 'rejected', 'cancelled')",
            name="ck_order_status",
        ),
        CheckConstraint("total_amount >= 0", name="ck_order_total"),
        UniqueConstraint("id", "restaurant_id", name="uq_order_id_restaurant"),
        UniqueConstraint("id", "session_id", "restaurant_id", name="uq_order_id_session_restaurant"),
        ForeignKeyConstraint(
            ["session_id", "restaurant_id"],
            ["table_sessions.id", "table_sessions.restaurant_id"],
            name="fk_order_session_restaurant",
        ),
        ForeignKeyConstraint(
            ["participant_id", "restaurant_id"],
            ["session_participants.id", "session_participants.restaurant_id"],
            name="fk_order_participant_restaurant",
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
        ForeignKey("table_sessions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("session_participants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    special_instructions: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        UniqueConstraint("id", "session_id", "restaurant_id", name="uq_order_item_id_session_restaurant"),
        ForeignKeyConstraint(
            ["order_id", "session_id", "restaurant_id"],
            ["orders.id", "orders.session_id", "orders.restaurant_id"],
            name="fk_order_item_order_session_restaurant",
        ),
        ForeignKeyConstraint(
            ["menu_item_id", "restaurant_id"],
            ["menu_items.id", "menu_items.restaurant_id"],
            name="fk_order_item_menu_restaurant",
        ),
        CheckConstraint("quantity > 0", name="ck_order_item_quantity"),
        CheckConstraint("unit_price >= 0", name="ck_order_item_unit_price"),
        CheckConstraint("line_total >= 0", name="ck_order_item_line_total"),
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
        Uuid, nullable=False, index=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    menu_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("menu_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    item_name: Mapped[str] = mapped_column(String(150), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    line_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
