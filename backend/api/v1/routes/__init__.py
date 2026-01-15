"""
API v1 Routes Package
"""
from fastapi import APIRouter
from .auth_routes import router as auth_router
from .referral_routes import router as referral_router
from .order_routes import router as order_router
from .webhook_routes import router as webhook_router

# Create main v1 router
api_v1_router = APIRouter(prefix="/api/v1")

# Include all sub-routers
api_v1_router.include_router(auth_router)
api_v1_router.include_router(referral_router)
api_v1_router.include_router(order_router)
api_v1_router.include_router(webhook_router)

__all__ = ["api_v1_router"]
