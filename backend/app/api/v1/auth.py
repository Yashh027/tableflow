import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)
from app.models.entities import Restaurant, User

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    restaurant_name: str = Field(min_length=2, max_length=150)
    restaurant_slug: str = Field(min_length=3, max_length=100)
    full_name: str = Field(min_length=2, max_length=150)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("restaurant_slug")
    @classmethod
    def validate_slug(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
            raise ValueError("Use lowercase letters, numbers and hyphens")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Enter a valid email address")
        return value


class LoginRequest(BaseModel):
    restaurant_slug: str = Field(min_length=3, max_length=100)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("restaurant_slug")
    @classmethod
    def validate_slug(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
            raise ValueError("Invalid restaurant slug")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Enter a valid email address")
        return value

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    restaurant = Restaurant(
        name=data.restaurant_name.strip(),
        slug=data.restaurant_slug,
    )

    user = User(
        id=uuid.uuid4(),
        full_name=data.full_name.strip(),
        email=data.email,
        password_hash=hash_password(data.password),
        role="owner",
        is_active=True,
    )

    try:
        db.add(restaurant)
        db.flush()

        user.restaurant_id = restaurant.id
        db.add(user)
        db.commit()
        db.refresh(restaurant)
        db.refresh(user)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Restaurant slug or account already exists",
        )

    return {
        "message": "Restaurant registered successfully",
        "restaurant_id": str(restaurant.id),
        "restaurant_slug": restaurant.slug,
        "owner_id": str(user.id),
    }


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    statement = (
        select(User, Restaurant)
        .join(Restaurant, User.restaurant_id == Restaurant.id)
        .where(
            Restaurant.slug == data.restaurant_slug.strip().lower(),
            User.email == data.email.strip().lower(),
        )
    )

    result = db.execute(statement).first()

    if not result:
        raise HTTPException(
            status_code=401,
            detail="Invalid restaurant, email or password",
        )

    user, restaurant = result

    if (
        not user.is_active
        or not restaurant.is_active
        or not verify_password(data.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid restaurant, email or password",
        )

    token = create_access_token(
        user.id,
        user.restaurant_id,
        user.role,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 1800,
        "user": {
            "id": str(user.id),
            "name": user.full_name,
            "email": user.email,
            "role": user.role,
            "restaurant_id": str(restaurant.id),
            "restaurant_name": restaurant.name,
        },
    }
