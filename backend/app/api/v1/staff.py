import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.entities import User
from app.models.orders import CustomerOrder, OrderItem

router = APIRouter(tags=["Staff and Kitchen"])


STAFF_ROLES = ("owner", "admin", "manager", "staff", "kitchen")


class OrderStatusUpdate(BaseModel):
    status: str


TRANSITIONS = {
    "pending": {"accepted", "rejected", "cancelled"},
    "accepted": {"preparing", "cancelled"},
    "preparing": {"ready"},
    "ready": {"served"},
    "served": {"completed"},
    "completed": set(),
    "rejected": set(),
    "cancelled": set(),
}


def order_details(order, db):
    items = db.scalars(
        select(OrderItem).where(OrderItem.order_id == order.id)
    ).all()

    return {
        "order_id": str(order.id),
        "session_id": str(order.session_id),
        "participant_id": str(order.participant_id),
        "status": order.status,
        "total_amount": str(order.total_amount),
        "special_instructions": order.special_instructions,
        "created_at": order.created_at,
        "items": [
            {
                "id": str(item.id),
                "name": item.item_name,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
                "line_total": str(item.line_total),
            }
            for item in items
        ],
    }


@router.get("/api/v1/staff/orders")
def staff_order_queue(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("owner", "admin", "manager", "staff")),
):
    orders = db.scalars(
        select(CustomerOrder)
        .where(CustomerOrder.restaurant_id == user.restaurant_id)
        .order_by(CustomerOrder.created_at.asc())
    ).all()

    return [order_details(order, db) for order in orders]


@router.patch("/api/v1/staff/orders/{order_id}/status")
def update_order_status(
    order_id: uuid.UUID,
    data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*STAFF_ROLES)),
):
    if user.restaurant_id is None:
        raise HTTPException(status_code=403, detail="Restaurant access required")

    new_status = data.status.strip().lower()

    valid_statuses = {
        "accepted", "preparing", "ready",
        "served", "completed", "rejected", "cancelled"
    }

    if new_status not in valid_statuses:
        raise HTTPException(status_code=422, detail="Invalid order status")

    # Kitchen staff can only manage preparation stages.
    if user.role == "kitchen" and new_status not in {"preparing", "ready"}:
        raise HTTPException(
            status_code=403,
            detail="Kitchen staff can only update preparation statuses",
        )

    order = db.scalar(
        select(CustomerOrder)
        .where(
            CustomerOrder.id == order_id,
            CustomerOrder.restaurant_id == user.restaurant_id,
        )
        .with_for_update()
    )

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if new_status not in TRANSITIONS.get(order.status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change order from {order.status} to {new_status}",
        )

    order.status = new_status
    db.commit()
    db.refresh(order)

    return {
        "message": "Order status updated",
        "order_id": str(order.id),
        "status": order.status,
    }


@router.get("/api/v1/kitchen/queue")
def kitchen_queue(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("owner", "admin", "manager", "kitchen")),
):
    if user.restaurant_id is None:
        raise HTTPException(status_code=403, detail="Restaurant access required")

    orders = db.scalars(
        select(CustomerOrder)
        .where(
            CustomerOrder.restaurant_id == user.restaurant_id,
            CustomerOrder.status.in_(["accepted", "preparing", "ready"]),
        )
        .order_by(CustomerOrder.created_at.asc())
    ).all()

    return [order_details(order, db) for order in orders]
