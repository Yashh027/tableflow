from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import Restaurant
from app.models.menu import MenuCategory, MenuItem

router = APIRouter(tags=["Public Restaurant Menu"])


@router.get("/api/v1/public/restaurants/{slug}/menu")
def get_public_menu(
    slug: str,
    db: Session = Depends(get_db),
):
    restaurant = db.scalar(
        select(Restaurant).where(
            Restaurant.slug == slug,
            Restaurant.is_active.is_(True),
        )
    )

    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    categories = db.scalars(
        select(MenuCategory)
        .where(
            MenuCategory.restaurant_id == restaurant.id,
            MenuCategory.is_active.is_(True),
        )
        .order_by(MenuCategory.display_order)
    ).all()

    items = db.scalars(
        select(MenuItem)
        .join(MenuCategory, MenuItem.category_id == MenuCategory.id)
        .where(
            MenuItem.restaurant_id == restaurant.id,
            MenuCategory.restaurant_id == restaurant.id,
            MenuCategory.is_active.is_(True),
            MenuItem.is_available.is_(True),
        )
        .order_by(MenuItem.name)
    ).all()

    return {
        "restaurant": {
            "name": restaurant.name,
            "slug": restaurant.slug,
            "currency": restaurant.currency,
        },
        "categories": [
            {
                "id": str(category.id),
                "name": category.name,
                "description": category.description,
                "display_order": category.display_order,
            }
            for category in categories
        ],
        "items": [
            {
                "id": str(item.id),
                "category_id": str(item.category_id),
                "name": item.name,
                "description": item.description,
                "price": str(item.price),
                "image_url": item.image_url,
                "vegetarian": item.is_vegetarian,
                "vegan": item.is_vegan,
                "available": item.is_available,
                "preparation_time": item.preparation_time_minutes,
            }
            for item in items
        ],
    }
