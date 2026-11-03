import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    String,
    Uuid,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Bill(Base):
    __tablename__ = "bills"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_bill_session"),
        UniqueConstraint("id", "restaurant_id", name="uq_bill_id_restaurant"),
        UniqueConstraint("id", "session_id", "restaurant_id", name="uq_bill_id_session_restaurant"),
        ForeignKeyConstraint(
            ["session_id", "restaurant_id"],
            ["table_sessions.id", "table_sessions.restaurant_id"],
            name="fk_bill_session_restaurant",
        ),
        CheckConstraint("total_amount >= 0", name="ck_bill_total"),
        CheckConstraint(
            "status IN ('unpaid', 'partially_paid', 'paid', 'void')",
            name="ck_bill_status",
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
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unpaid"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False
    )


class BillItem(Base):
    __tablename__ = "bill_items"
    __table_args__ = (
        ForeignKeyConstraint(
            ["bill_id", "session_id", "restaurant_id"],
            ["bills.id", "bills.session_id", "bills.restaurant_id"],
            name="fk_bill_item_bill_session_restaurant",
        ),
        ForeignKeyConstraint(
            ["order_item_id", "session_id", "restaurant_id"],
            ["order_items.id", "order_items.session_id", "order_items.restaurant_id"],
            name="fk_bill_item_order_item_session_restaurant",
        ),
        UniqueConstraint("order_item_id", name="uq_bill_item_order_item"),
        CheckConstraint("quantity > 0", name="ck_bill_item_quantity"),
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
    bill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("bills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("order_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    item_name: Mapped[str] = mapped_column(String(150), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    line_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_payment_amount"),
        ForeignKeyConstraint(
            ["bill_id", "restaurant_id"],
            ["bills.id", "bills.restaurant_id"],
            name="fk_payment_bill_restaurant",
        ),
        CheckConstraint(
            "method IN ('cash', 'upi', 'card', 'online')",
            name="ck_payment_method",
        ),
        CheckConstraint(
            "status IN ('pending', 'succeeded', 'failed', 'refunded')",
            name="ck_payment_status",
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
    bill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("bills.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    reference: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
