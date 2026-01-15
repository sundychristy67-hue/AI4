from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from config import settings
from database import connect_to_db, close_db_connection
import logging

# Import routers
from routes.auth_routes import router as auth_router
from routes.client_routes import router as client_router
from routes.portal_routes import router as portal_router
from routes.admin_routes import router as admin_router
from routes.telegram_routes import router as telegram_router
from routes.telegram_admin_routes import router as telegram_admin_router
from routes.settings_routes import router as settings_router
from routes.public_routes import router as public_router
from routes.test_routes import router as test_router

# Import API v1
from api.v1 import api_v1_router, init_api_v1_db, close_api_v1_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Gaming Platform API",
    description="""
## Gaming Platform & Referral Order System API

This API provides two main systems:

### Portal API (Legacy)
- Client and admin authentication
- Game management
- Wallet and transaction management
- Referral system

### API v1 - Referral-Based Gaming Order System
A production-ready REST API for managing gaming orders with referral bonuses.

**Base URL**: `/api/v1`

**Key Features**:
- Magic link + password authentication
- Referral code validation with perks
- Order validation and creation with bonus engine
- HMAC-signed webhook notifications

**Authentication**:
All endpoints (except signup) require either:
- `username` + `password` in request body, OR
- `Authorization: Bearer <token>` header

See individual endpoint documentation for details.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Authentication", "description": "User signup, login, and token management"},
        {"name": "Referrals", "description": "Referral code validation and perk lookup"},
        {"name": "Orders", "description": "Order validation, creation, and management"},
        {"name": "Webhooks", "description": "Webhook registration and delivery"},
    ]
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.cors_origins.split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    await connect_to_db()
    await init_api_v1_db()  # Initialize API v1 database
    logger.info("Application startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    await close_db_connection()
    await close_api_v1_db()  # Close API v1 database
    logger.info("Application shutdown complete")

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "Portal & Automation API is running", "database": "PostgreSQL"}

# Include all routers with /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(client_router, prefix="/api")
app.include_router(portal_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(telegram_router, prefix="/api")
app.include_router(telegram_admin_router, prefix="/api/admin")
app.include_router(settings_router, prefix="/api")
app.include_router(public_router, prefix="/api")
app.include_router(test_router, prefix="/api/admin")

# Include API v1 router
app.include_router(api_v1_router)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Portal & Automation API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/api/")
async def api_root():
    return {
        "message": "Portal & Automation API",
        "endpoints": {
            "auth": "/api/auth",
            "clients": "/api/clients",
            "portal": "/api/portal",
            "admin": "/api/admin",
            "telegram": "/api/telegram"
        }
    }
