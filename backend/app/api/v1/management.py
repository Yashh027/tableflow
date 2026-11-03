import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.entities import User, DiningTable

router = APIRouter(prefix="/management", tags=["Restaurant Management"])

@router.get("/tables")
def list_tables(db: Session = Depends(get_db), user: User = Depends(require_roles("owner", "admin", "manager", "staff"))):
    if user.restaurant_id is None:
        raise HTTPException(status_code=403, detail="Restaurant access required")
    rows = db.scalars(select(DiningTable).where(DiningTable.restaurant_id == user.restaurant_id).order_by(DiningTable.table_number)).all()
    return [{"id": str(t.id), "table_number": t.table_number, "capacity": t.capacity, "is_active": t.is_active} for t in rows]

@router.patch("/tables/{table_id}/status")
def set_table_status(table_id: uuid.UUID, active: bool, db: Session = Depends(get_db), user: User = Depends(require_roles("owner", "admin", "manager"))):
    table = db.scalar(select(DiningTable).where(DiningTable.id == table_id, DiningTable.restaurant_id == user.restaurant_id))
    if table is None:
        raise HTTPException(status_code=404, detail="Table not found")
    table.is_active = active
    db.commit()
    return {"id": str(table.id), "is_active": table.is_active}
