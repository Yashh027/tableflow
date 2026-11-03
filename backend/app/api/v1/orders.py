import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.guest_auth import get_current_guest
from app.models.sessions import SessionParticipant, TableSession
from app.models.billing import Bill
from app.models.menu import MenuItem, MenuCategory
from app.models.orders import CustomerOrder, OrderItem

router = APIRouter(prefix="/customer/orders", tags=["Customer Orders"])


class OrderLineInput(BaseModel):
    menu_item_id: uuid.UUID
    quantity: int = Field(ge=1, le=50)


class OrderCreate(BaseModel):
    items: list[OrderLineInput] = Field(min_length=1, max_length=30)
    special_instructions: str | None = Field(default=None, max_length=1000)

    @field_validator("items")
    @classmethod
    def unique_menu_items(cls, items):
        ids = [item.menu_item_id for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("Each menu item must appear only once")
        return items


@router.post("", status_code=status.HTTP_201_CREATED)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    guest: SessionParticipant = Depends(get_current_guest),
):
    # Serialize order placement against bill creation/closure. Both operations
    # lock this same session row, preventing orders arriving after the bill snapshot.
    session = db.scalar(
        select(TableSession)
        .where(
            TableSession.id == guest.session_id,
            TableSession.restaurant_id == guest.restaurant_id,
            TableSession.status == "active",
        )
        .with_for_update()
    )
    if session is None:
        raise HTTPException(status_code=409, detail="This table session is closing or closed")

    existing_bill = db.scalar(
        select(Bill.id).where(
            Bill.session_id == session.id,
            Bill.restaurant_id == guest.restaurant_id,
        )
    )
    if existing_bill is not None:
        raise HTTPException(status_code=409, detail="A bill has already been created for this session")

    requested_ids = [line.menu_item_id for line in data.items]

    menu_items = db.scalars(
        select(MenuItem)
        .join(MenuCategory, MenuItem.category_id == MenuCategory.id)
        .where(
            MenuItem.id.in_(requested_ids),
            MenuItem.restaurant_id == guest.restaurant_id,
            MenuCategory.restaurant_id == guest.restaurant_id,
            MenuCategory.is_active.is_(True),
            MenuItem.is_available.is_(True),
        )
    ).all()

    items_by_id = {item.id: item for item in menu_items}

    if len(items_by_id) != len(requested_ids):
        raise HTTPException(
            status_code=400,
            detail="One or more menu items are unavailable",
        )

    total = Decimal("0.00")
    order_lines = []

    for line in data.items:
        menu_item = items_by_id[line.menu_item_id]

        # Price always comes from the database, never from the customer.
        unit_price = menu_item.price
        line_total = unit_price * line.quantity
        total += line_total

        order_lines.append({
            "menu_item_id": menu_item.id,
            "item_name": menu_item.name,
            "quantity": line.quantity,
            "unit_price": unit_price,
            "line_total": line_total,
        })

    order = CustomerOrder(
        restaurant_id=guest.restaurant_id,
        session_id=guest.session_id,
        participant_id=guest.id,
        status="pending",
        total_amount=total,
        special_instructions=data.special_instructions,
    )

    try:
        db.add(order)
        db.flush()

        for line in order_lines:
            db.add(OrderItem(
                order_id=order.id,
                restaurant_id=guest.restaurant_id,
                session_id=guest.session_id,
                **line,
            ))

        db.commit()
        db.refresh(order)

    except Exception:
        db.rollback()
        raise

    return {
        "message": "Order placed successfully",
        "order_id": str(order.id),
        "session_id": str(order.session_id),
        "status": order.status,
        "total_amount": str(order.total_amount),
        "currency": "INR",
        "items": [
            {
                "name": line["item_name"],
                "quantity": line["quantity"],
                "unit_price": str(line["unit_price"]),
                "line_total": str(line["line_total"]),
            }
            for line in order_lines
        ],
    }


@router.get("")
def list_my_orders(
    db: Session = Depends(get_db),
    guest: SessionParticipant = Depends(get_current_guest),
):
    orders = db.scalars(
        select(CustomerOrder)
        .where(
            CustomerOrder.participant_id == guest.id,
            CustomerOrder.restaurant_id == guest.restaurant_id,
        )
        .order_by(CustomerOrder.created_at.desc())
    ).all()

    return [
        {
            "order_id": str(order.id),
            "status": order.status,
            "total_amount": str(order.total_amount),
            "created_at": order.created_at,
        }
        for order in orders
    ]
