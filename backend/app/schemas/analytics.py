"""
Pydantic schemas for Analytics API requests and responses
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ========================================
# DiD Analysis Schemas
# ========================================


class DiDRequest(BaseModel):
    """Request schema for DiD analysis"""
    
    treatment_game_id: int = Field(..., description="Game ID for treatment group")
    control_game_ids: Optional[List[int]] = Field(
        None,
        description="List of game IDs for control group (auto-selected if not provided)"
    )
    pre_periods: int = Field(
        6,
        ge=3,
        le=24,
        description="Number of months before discount event"
    )
    post_periods: int = Field(
        3,
        ge=1,
        le=12,
        description="Number of months after discount event"
    )
    discount_threshold: float = Field(
        0.25,
        ge=0.0,
        le=1.0,
        description="Minimum discount percentage to consider (0.25 = 25%)"
    )


class DiDResponse(BaseModel):
    """Response schema for DiD analysis results"""
    
    result_id: int = Field(..., description="Analysis result ID")
    analysis_type: str = "did"
    game_id: int
    parameters: Dict[str, Any] = Field(..., description="Analysis parameters")
    results: Dict[str, Any] = Field(..., description="DiD estimation results")
    executed_at: datetime
    model_version: str
    
    model_config = ConfigDict(from_attributes=True)


# ========================================
# Survival Analysis Schemas
# ========================================


class SurvivalRequest(BaseModel):
    """Request schema for Survival analysis"""
    
    game_ids: Optional[List[int]] = Field(
        None,
        description="Specific game IDs to analyze (all games if not provided)"
    )
    genre: Optional[str] = Field(
        None,
        description="Filter by genre for genre-level analysis"
    )
    churn_threshold_pct: float = Field(
        0.5,
        ge=0.1,
        le=0.9,
        description="Player count decline threshold to consider churn (0.5 = 50% decline)"
    )
    groupby_col: Optional[str] = Field(
        None,
        description="Column to group by (genre_name, developer, etc.)"
    )


class SurvivalResponse(BaseModel):
    """Response schema for Survival analysis results"""
    
    result_id: int
    analysis_type: str = "kaplan_meier"
    genre_id: Optional[int] = None
    parameters: Dict[str, Any]
    results: Dict[str, Any] = Field(
        ...,
        description="Survival curves, retention metrics, Cox PH results"
    )
    executed_at: datetime
    model_version: str
    
    model_config = ConfigDict(from_attributes=True)


# ========================================
# Elasticity Analysis Schemas
# ========================================


class ElasticityRequest(BaseModel):
    """Request schema for Price Elasticity analysis"""
    
    genre: Optional[str] = Field(
        None,
        description="Analyze specific genre (all genres if not provided)"
    )
    method: str = Field(
        "log_log",
        description="Regression method (log_log, linear, arc_elasticity)"
    )
    group_by: Optional[str] = Field(
        "genre_name",
        description="Group elasticity by column (genre_name, developer, etc.)"
    )
    min_price: Optional[float] = Field(
        None,
        ge=0.0,
        description="Minimum price filter"
    )
    max_price: Optional[float] = Field(
        None,
        description="Maximum price filter"
    )


class ElasticityResponse(BaseModel):
    """Response schema for Price Elasticity results"""
    
    result_id: int
    analysis_type: str = "elasticity"
    genre_id: Optional[int] = None
    parameters: Dict[str, Any]
    results: Dict[str, Any] = Field(
        ...,
        description="Elasticity coefficients, optimal pricing recommendations"
    )
    executed_at: datetime
    model_version: str
    
    model_config = ConfigDict(from_attributes=True)


# ========================================
# Analysis List/History Schemas
# ========================================


class AnalysisListItem(BaseModel):
    """Minimal analysis info for list views"""
    
    result_id: int
    analysis_type: str
    game_id: Optional[int] = None
    genre_id: Optional[int] = None
    executed_at: datetime
    model_version: str
    
    model_config = ConfigDict(from_attributes=True)


class AnalysisListResponse(BaseModel):
    """Paginated analysis results list"""
    
    results: List[AnalysisListItem]
    total: int
    page: int
    page_size: int
