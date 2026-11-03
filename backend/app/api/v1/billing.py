import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.entities import User
from app.models.sessions import TableSession
from app.models.orders import CustomerOrder, OrderItem
from app.models.billing import Bill, BillItem, Payment

router = APIRouter(tags=["Billing and Payments"])

BILLING_ROLES = ("owner", "admin", "manager", "staff")


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    method: str
    reference: str | None = Field(default=None, max_length=255)


def get_bill_payment_totals(db: Session, bill_id):
    totals = db.execute(
        select(
            func.coalesce(
                func.sum(Payment.amount).filter(
                    Payment.status == "succeeded"
                ), 0
            ),
            func.coalesce(
                func.sum(Payment.amount).filter(
                    Payment.status == "pending"
                ), 0
            ),
        ).where(Payment.bill_id == bill_id)
    ).one()

    return Decimal(str(totals[0])), Decimal(str(totals[1]))


def refresh_bill_status(db: Session, bill: Bill):
    paid, pending = get_bill_payment_totals(db, bill.id)

    if paid >= bill.total_amount:
        bill.status = "paid"
    elif paid > 0 or pending > 0:
        bill.status = "partially_paid"
    else:
        bill.status = "unpaid"

    return paid, pending


def bill_response(db: Session, bill: Bill):
    items = db.scalars(
        select(BillItem).where(BillItem.bill_id == bill.id)
    ).all()

    paid, pending = get_bill_payment_totals(db, bill.id)

    payments = db.scalars(
        select(Payment)
        .where(Payment.bill_id == bill.id)
        .order_by(Payment.created_at.desc())
    ).all()

    return {
        "bill_id": str(bill.id),
        "session_id": str(bill.session_id),
        "total_amount": str(bill.total_amount),
        "paid_amount": str(paid),
        "pending_amount": str(pending),
        "remaining_amount": str(max(
            Decimal("0.00"), bill.total_amount - paid
        )),
        "status": bill.status,
        "items": [
            {
                "name": item.item_name,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
                "line_total": str(item.line_total),
            }
            for item in items
        ],
        "payments": [
            {
                "payment_id": str(p.id),
                "amount": str(p.amount),
                "method": p.method,
                "status": p.status,
                "reference": p.reference,
            }
            for p in payments
        ],
    }


@router.post("/api/v1/staff/billing/{session_id}/create")
def create_bill(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*BILLING_ROLES)),
):
    if user.restaurant_id is None:
        raise HTTPException(status_code=403, detail="Restaurant access required")

    session = db.scalar(
        select(TableSession).where(
            TableSession.id == session_id,
            TableSession.restaurant_id == user.restaurant_id,
        )
        .with_for_update()
    )

    if session is None:
        raise HTTPException(status_code=404, detail="Table session not found")
    if session.status == "closed":
        raise HTTPException(status_code=409, detail="Table session is already closed")

    existing = db.scalar(
        select(Bill).where(
            Bill.session_id == session_id,
            Bill.restaurant_id == user.restaurant_id,
        )
    )

    if existing:
        return bill_response(db, existing)

    orders = db.scalars(
        select(CustomerOrder).where(
            CustomerOrder.session_id == session_id,
            CustomerOrder.restaurant_id == user.restaurant_id,
            CustomerOrder.status.notin_(["rejected", "cancelled"]),
        )
    ).all()

    if not orders:
        raise HTTPException(status_code=400, detail="No billable orders found")

    order_ids = [order.id for order in orders]

    order_items = db.scalars(
        select(OrderItem).where(OrderItem.order_id.in_(order_ids))
    ).all()

    if not order_items:
        raise HTTPException(status_code=400, detail="No order items found")

    total = sum(
        (item.line_total for item in order_items),
        Decimal("0.00"),
    )

    bill = Bill(
        restaurant_id=user.restaurant_id,
        session_id=session_id,
        total_amount=total,
        status="unpaid",
    )

    try:
        db.add(bill)
        db.flush()

        for item in order_items:
            db.add(
                BillItem(
                    bill_id=bill.id,
                    restaurant_id=user.restaurant_id,
                    session_id=session_id,
                    order_item_id=item.id,
                    item_name=item.item_name,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    line_total=item.line_total,
                )
            )

        # Stop new customer orders once the bill snapshot is committed.
        session.status = "closing"
        db.commit()
        db.refresh(bill)

    except Exception:
        db.rollback()
        raise

    return bill_response(db, bill)


@router.get("/api/v1/staff/billing/{bill_id}")
def get_bill(
    bill_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*BILLING_ROLES)),
):
    bill = db.scalar(
        select(Bill).where(
            Bill.id == bill_id,
            Bill.restaurant_id == user.restaurant_id,
        )
    )

    if bill is None:
        raise HTTPException(status_code=404, detail="Bill not found")

    return bill_response(db, bill)


@router.post("/api/v1/staff/billing/{bill_id}/payments")
def record_payment(
    bill_id: uuid.UUID,
    data: PaymentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*BILLING_ROLES)),
):
    if user.restaurant_id is None:
        raise HTTPException(status_code=403, detail="Restaurant access required")

    method = data.method.strip().lower()

    if method not in {"cash", "upi", "card", "online"}:
        raise HTTPException(status_code=422, detail="Unsupported payment method")

    bill = db.scalar(
        select(Bill)
        .where(
            Bill.id == bill_id,
            Bill.restaurant_id == user.restaurant_id,
        )
        .with_for_update()
    )

    if bill is None:
        raise HTTPException(status_code=404, detail="Bill not found")

    if bill.status in {"paid", "void"}:
        raise HTTPException(status_code=409, detail="Bill cannot accept payments")

    paid, pending = get_bill_payment_totals(db, bill.id)
    remaining = bill.total_amount - paid - pending

    if data.amount > remaining:
        raise HTTPException(
            status_code=400,
            detail=f"Payment exceeds remaining balance of {remaining}",
        )

    # Offline methods are recorded by authorized staff as received.
    # Online payments remain pending until a verified gateway webhook arrives.
    payment_status = "pending" if method == "online" else "succeeded"

    payment = Payment(
        restaurant_id=user.restaurant_id,
        bill_id=bill.id,
        amount=data.amount,
        method=method,
        status=payment_status,
        reference=data.reference,
        recorded_by=user.id,
    )

    db.add(payment)
    db.flush()

    refresh_bill_status(db, bill)

    if bill.status == "paid":
        session = db.scalar(
            select(TableSession)
            .where(
                TableSession.id == bill.session_id,
                TableSession.restaurant_id == user.restaurant_id,
            )
            .with_for_update()
        )
        if session is not None:
            session.status = "closed"
            session.closed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(payment)
    db.refresh(bill)

    return {
        "message": "Payment recorded",
        "payment_id": str(payment.id),
        "payment_status": payment.status,
        "bill_status": bill.status,
        "bill": bill_response(db, bill),
    }
