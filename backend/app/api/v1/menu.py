from decimal import Decimal
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.entities import User
from app.models.menu import MenuCategory, MenuItem

router = APIRouter(prefix="/menu", tags=["Menu Management"])


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None
    display_order: int = 0


class MenuItemCreate(BaseModel):
    category_id: uuid.UUID
    name: str = Field(min_length=2, max_length=150)
    description: str | None = None
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    image_url: str | None = None
    is_vegetarian: bool = False
    is_vegan: bool = False
    preparation_time_minutes: int = Field(default=15, ge=1, le=240)


def require_restaurant(user: User):
    if user.restaurant_id is None:
        raise HTTPException(status_code=403, detail="Restaurant access required")
    return user.restaurant_id


@router.post("/categories", status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    restaurant_id = require_restaurant(user)

    category = MenuCategory(
        restaurant_id=restaurant_id,
        name=data.name.strip(),
        description=data.description,
        display_order=data.display_order,
    )

    db.add(category)
    try:
        db.commit()
        db.refresh(category)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Could not create category")

    return {
        "id": str(category.id),
        "name": category.name,
        "restaurant_id": str(category.restaurant_id),
    }


@router.get("/categories")
def list_categories(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    restaurant_id = require_restaurant(user)

    categories = db.scalars(
        select(MenuCategory)
        .where(
            MenuCategory.restaurant_id == restaurant_id,
            MenuCategory.is_active.is_(True),
        )
        .order_by(MenuCategory.display_order, MenuCategory.name)
    ).all()

    return [
        {
            "id": str(c.id),
            "name": c.name,
            "description": c.description,
            "display_order": c.display_order,
        }
        for c in categories
    ]


@router.post("/items", status_code=status.HTTP_201_CREATED)
def create_menu_item(
    data: MenuItemCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    restaurant_id = require_restaurant(user)

    category = db.scalar(
        select(MenuCategory).where(
            MenuCategory.id == data.category_id,
            MenuCategory.restaurant_id == restaurant_id,
            MenuCategory.is_active.is_(True),
        )
    )

    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    item = MenuItem(
        restaurant_id=restaurant_id,
        category_id=category.id,
        name=data.name.strip(),
        description=data.description,
        price=data.price,
        image_url=data.image_url,
        is_vegetarian=data.is_vegetarian,
        is_vegan=data.is_vegan,
        preparation_time_minutes=data.preparation_time_minutes,
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "id": str(item.id),
        "name": item.name,
        "price": str(item.price),
        "category_id": str(item.category_id),
    }


@router.get("/items")
def list_menu_items(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    restaurant_id = require_restaurant(user)

    items = db.scalars(
        select(MenuItem)
        .where(MenuItem.restaurant_id == restaurant_id)
        .order_by(MenuItem.display_order, MenuItem.name)
    ).all()

    return [
        {
            "id": str(item.id),
            "category_id": str(item.category_id),
            "name": item.name,
            "description": item.description,
            "price": str(item.price),
            "is_vegetarian": item.is_vegetarian,
            "is_vegan": item.is_vegan,
            "is_available": item.is_available,
            "preparation_time_minutes": item.preparation_time_minutes,
        }
        for item in items
    ]

class MenuAvailabilityUpdate(BaseModel):
    is_available: bool


@router.patch("/items/{item_id}/availability")
def update_menu_item_availability(
    item_id: uuid.UUID,
    data: MenuAvailabilityUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    restaurant_id = require_restaurant(user)
    item = db.scalar(select(MenuItem).where(
        MenuItem.id == item_id,
        MenuItem.restaurant_id == restaurant_id,
    ))
    if item is None:
        raise HTTPException(status_code=404, detail="Menu item not found")
    item.is_available = data.is_available
    db.commit()
    db.refresh(item)
    return {"id": str(item.id), "is_available": item.is_available}
