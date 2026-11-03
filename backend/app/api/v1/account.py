from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user,
    get_current_restaurant,
)
from app.models.entities import User, Restaurant

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me")
def get_my_account(
    user: User = Depends(get_current_user),
    restaurant: Restaurant = Depends(get_current_restaurant),
):
    return {
        "user_id": str(user.id),
        "name": user.full_name,
        "email": user.email,
        "role": user.role,
        "restaurant": {
            "id": str(restaurant.id),
            "name": restaurant.name,
            "slug": restaurant.slug,
        },
    }
