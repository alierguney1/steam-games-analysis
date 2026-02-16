"""
Main API Router
Aggregates all API endpoints
"""

from fastapi import APIRouter

# Import endpoint routers
from app.api import games, analytics, ingestion, dashboard

api_router = APIRouter()

# Include sub-routers
api_router.include_router(games.router, prefix="/games", tags=["games"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])


@api_router.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Steam Analytics API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "endpoints": {
            "games": "/api/games",
            "analytics": "/api/analytics",
            "ingestion": "/api/ingestion",
            "dashboard": "/api/dashboard",
        },
    }


@api_router.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

