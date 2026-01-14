from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import connect_to_mongo, close_mongo_connection
import logging

# Import routers
from routes.auth_routes import router as auth_router
from routes.client_routes import router as client_router
from routes.portal_routes import router as portal_router
from routes.admin_routes import router as admin_router
from routes.telegram_routes import router as telegram_router
from routes.settings_routes import router as settings_router
from routes.public_routes import router as public_router
from routes.test_routes import router as test_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Portal & Automation API",
    description="Staffless-first platform API for Messenger → Portal → Telegram ecosystem",
    version="1.0.0"
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
    await connect_to_mongo()
    logger.info("Application startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()
    logger.info("Application shutdown complete")

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "Portal & Automation API is running"}

# Include all routers with /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(client_router, prefix="/api")
app.include_router(portal_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(telegram_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(public_router, prefix="/api")

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
