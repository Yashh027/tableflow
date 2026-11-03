import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.auth import router as auth_router
from app.api.v1.account import router as account_router
from app.api.v1.menu import router as menu_router
from app.api.v1.sessions import router as sessions_router
from app.api.v1.orders import router as orders_router
from app.api.v1.staff import router as staff_router
from app.api.v1.billing import router as billing_router
from app.api.v1.management import router as management_router


app = FastAPI(
    title="TableFlow API",
    description="Restaurant ordering and management platform",
    version="1.0.0",
)


# Restrict browser access to explicitly configured frontend origins.
cors_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
if not cors_origins:
    raise RuntimeError("CORS_ORIGINS must contain at least one trusted origin")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(account_router, prefix="/api/v1")
app.include_router(menu_router, prefix="/api/v1")
app.include_router(sessions_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(staff_router)
app.include_router(billing_router)
app.include_router(management_router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "TableFlow API is running"}


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "healthy", "database": "connected"}

from app.api.v1.service_requests import router as service_requests_router
app.include_router(service_requests_router)

from app.api.v1.realtime import router as realtime_router
app.include_router(realtime_router)


from app.api.v1.public_menu import router as public_menu_router
app.include_router(public_menu_router)
