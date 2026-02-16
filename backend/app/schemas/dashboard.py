"""
Pydantic schemas for Dashboard API requests and responses
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict


# ========================================
# Dashboard Summary Schemas
# ========================================


class KPICard(BaseModel):
    """Key Performance Indicator card"""
    
    title: str = Field(..., description="KPI title")
    value: Any = Field(..., description="Current value")
    change: Optional[float] = Field(None, description="Percent change from previous period")
    trend: Optional[str] = Field(None, description="Trend direction (up, down, stable)")
    format: str = Field("number", description="Display format (number, currency, percentage)")


class DashboardSummary(BaseModel):
    """Dashboard summary with KPIs"""
    
    total_games: int = Field(..., description="Total games in database")
    total_facts: int = Field(..., description="Total fact records")
    avg_concurrent_players: int = Field(..., description="Average concurrent players across all games")
    active_discount_count: int = Field(..., description="Number of games currently on discount")
    avg_discount_pct: float = Field(..., description="Average discount percentage")
    latest_data_date: Optional[date] = Field(None, description="Most recent data date")
    kpis: List[KPICard] = Field(default=[], description="Additional KPI cards")


# ========================================
# Time Series Schemas
# ========================================


class TimeSeriesPoint(BaseModel):
    """Single point in time series"""
    
    date: date
    value: float
    label: Optional[str] = None


class TimeSeriesData(BaseModel):
    """Time series data for charts"""
    
    series_name: str
    data: List[TimeSeriesPoint]
    metadata: Optional[Dict[str, Any]] = None


class TimeSeriesResponse(BaseModel):
    """Response with multiple time series"""
    
    series: List[TimeSeriesData]
    date_range: Dict[str, date] = Field(
        ...,
        description="Date range (start_date, end_date)"
    )


# ========================================
# Top Games Schemas
# ========================================


class TopGameItem(BaseModel):
    """Top game item for leaderboards"""
    
    game_id: int
    appid: int
    name: str
    metric_value: float = Field(..., description="Value of the metric being ranked by")
    metric_name: str = Field(..., description="Name of the metric")
    current_price: Optional[float] = None
    discount_pct: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)


class TopGamesResponse(BaseModel):
    """Response with top games by various metrics"""
    
    top_by_players: List[TopGameItem] = Field(
        default=[],
        description="Top games by player count"
    )
    top_by_growth: List[TopGameItem] = Field(
        default=[],
        description="Top games by player growth"
    )
    top_discounted: List[TopGameItem] = Field(
        default=[],
        description="Top discounted games"
    )
    limit: int = Field(10, description="Number of items in each category")


# ========================================
# Genre Distribution Schemas
# ========================================


class GenreDistribution(BaseModel):
    """Genre distribution data"""
    
    genre_name: str
    game_count: int
    avg_players: Optional[int] = None
    avg_price: Optional[float] = None
    total_players: Optional[int] = None


class GenreDistributionResponse(BaseModel):
    """Response with genre distribution"""
    
    distributions: List[GenreDistribution]
    total_genres: int


# ========================================
# Analysis Summary Schemas
# ========================================


class AnalysisSummaryItem(BaseModel):
    """Summary of analysis results"""
    
    analysis_type: str
    count: int = Field(..., description="Number of analyses of this type")
    last_executed: Optional[datetime] = None
    avg_execution_time: Optional[float] = Field(
        None,
        description="Average execution time in seconds"
    )


class AnalysisSummaryResponse(BaseModel):
    """Response with analysis summary"""
    
    analyses: List[AnalysisSummaryItem]
    total_analyses: int


# ========================================
# Comprehensive Dashboard Response
# ========================================


class DashboardResponse(BaseModel):
    """Comprehensive dashboard data"""
    
    summary: DashboardSummary
    top_games: TopGamesResponse
    genre_distribution: GenreDistributionResponse
    recent_analyses: List[AnalysisSummaryItem]
    generated_at: datetime = Field(default_factory=datetime.utcnow)
