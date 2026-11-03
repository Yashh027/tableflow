import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import JWT_SECRET_KEY, JWT_ALGORITHM
from app.models.entities import User, Restaurant

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme)
    ],
    db: Session = Depends(get_db),
):
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )
        user_id = uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, KeyError, TypeError):
        raise unauthorized

    user = db.scalar(
        select(User).where(User.id == user_id)
    )

    if user is None or not user.is_active:
        raise unauthorized

    if str(user.restaurant_id) != payload.get("restaurant_id"):
        raise unauthorized

    if user.restaurant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Restaurant access is required",
        )

    restaurant = db.scalar(
        select(Restaurant).where(
            Restaurant.id == user.restaurant_id,
            Restaurant.is_active.is_(True),
        )
    )

    if restaurant is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Restaurant is unavailable",
        )

    return user


def require_roles(*allowed_roles):
    def role_checker(user: User = Depends(get_current_user)):
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return role_checker


def get_current_restaurant(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.restaurant_id is None:
        raise HTTPException(
            status_code=403,
            detail="Restaurant access is required",
        )

    restaurant = db.scalar(
        select(Restaurant).where(
            Restaurant.id == user.restaurant_id,
            Restaurant.is_active.is_(True),
        )
    )

    if restaurant is None:
        raise HTTPException(
            status_code=403,
            detail="Restaurant is unavailable",
        )

    return restaurant
