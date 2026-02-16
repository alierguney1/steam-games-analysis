"""
Pydantic schemas for Ingestion API requests and responses
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


# ========================================
# Enums
# ========================================


class IngestionStatus(str, Enum):
    """Ingestion job status"""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DataSource(str, Enum):
    """Data source types"""
    
    STEAMSPY = "steamspy"
    STEAMCHARTS = "steamcharts"
    STEAM_STORE = "steam_store"


# ========================================
# Request Schemas
# ========================================


class IngestionTriggerRequest(BaseModel):
    """Request to trigger manual ingestion"""
    
    appids: Optional[List[int]] = Field(
        None,
        description="Specific app IDs to fetch (all if not provided)"
    )
    sources: List[DataSource] = Field(
        default=[DataSource.STEAMSPY, DataSource.STEAMCHARTS, DataSource.STEAM_STORE],
        description="Data sources to fetch from"
    )
    force_refresh: bool = Field(
        default=False,
        description="Force refresh even if recent data exists"
    )


# ========================================
# Response Schemas
# ========================================


class IngestionStats(BaseModel):
    """Statistics from ingestion job"""
    
    games_fetched: int = Field(0, description="Number of games fetched")
    games_created: int = Field(0, description="Number of new games created")
    games_updated: int = Field(0, description="Number of games updated")
    facts_created: int = Field(0, description="Number of new fact records")
    tags_created: int = Field(0, description="Number of new tags created")
    genres_created: int = Field(0, description="Number of new genres created")
    errors: List[str] = Field(default=[], description="List of errors encountered")


class IngestionJobResponse(BaseModel):
    """Response for ingestion job"""
    
    job_id: str = Field(..., description="Unique job identifier")
    status: IngestionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    stats: Optional[IngestionStats] = None
    error_message: Optional[str] = None


class IngestionStatusResponse(BaseModel):
    """Current status of ingestion pipeline"""
    
    last_full_etl: Optional[datetime] = Field(
        None,
        description="Last time full ETL completed"
    )
    last_price_sync: Optional[datetime] = Field(
        None,
        description="Last time price sync completed"
    )
    total_games: int = Field(0, description="Total games in database")
    total_facts: int = Field(0, description="Total fact records in database")
    recent_jobs: List[IngestionJobResponse] = Field(
        default=[],
        description="Recent ingestion jobs"
    )
    is_running: bool = Field(False, description="Is ingestion currently running")


# ========================================
# Data Quality Schemas
# ========================================


class DataQualityMetrics(BaseModel):
    """Data quality metrics"""
    
    total_games: int
    games_with_price_data: int
    games_with_player_data: int
    games_missing_metadata: int
    oldest_fact_date: Optional[datetime] = None
    newest_fact_date: Optional[datetime] = None
    avg_facts_per_game: float
    
    
class DataQualityResponse(BaseModel):
    """Response with data quality information"""
    
    metrics: DataQualityMetrics
    recommendations: List[str] = Field(
        default=[],
        description="Recommendations to improve data quality"
    )
