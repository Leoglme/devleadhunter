"""
Main API v1 router.
"""
from fastapi import APIRouter
from .routes import health, prospects, auth, users
from core.config import settings


router = APIRouter(
    prefix="",
    tags=["v1"]
)


# Include all route modules
router.include_router(auth.router)
router.include_router(health.router)
router.include_router(prospects.router)
router.include_router(users.router)

