"""
Steam Analytics Backend Application
Main FastAPI application factory with lifespan events
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.api.router import api_router
from app.db.session import engine, init_db


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("Starting Steam Analytics Backend...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Database: {settings.DATABASE_URL.split('@')[-1]}")

    # Initialize database
    await init_db()
    logger.info("Database initialized successfully")

    # TODO: Start scheduler for ETL jobs
    # scheduler.start()

    yield

    # Shutdown
    logger.info("Shutting down Steam Analytics Backend...")
    # TODO: Shutdown scheduler
    # scheduler.shutdown()

    # Close database connections
    await engine.dispose()
    logger.info("Database connections closed")


def create_app() -> FastAPI:
    """
    FastAPI application factory
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Steam Games Player Retention and Causal Pricing Analysis API",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API router
    app.include_router(api_router, prefix="/api")

    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "environment": settings.ENVIRONMENT,
            "version": settings.VERSION,
        }

    return app


app = create_app()
