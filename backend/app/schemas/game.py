"""
Pydantic schemas for Game-related API requests and responses
"""

from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict


# ========================================
# Base Models
# ========================================


class GameBase(BaseModel):
    """Base game schema with common fields"""
    
    appid: int = Field(..., description="Steam App ID")
    name: str = Field(..., description="Game name", max_length=500)
    developer: Optional[str] = Field(None, description="Developer name", max_length=500)
    publisher: Optional[str] = Field(None, description="Publisher name", max_length=500)
    release_date: Optional[date] = Field(None, description="Release date")
    is_free: bool = Field(default=False, description="Is the game free to play")


class GameCreate(GameBase):
    """Schema for creating a new game"""
    
    steamspy_owners_min: Optional[int] = Field(None, description="Min estimated owners (SteamSpy)")
    steamspy_owners_max: Optional[int] = Field(None, description="Max estimated owners (SteamSpy)")
    positive_reviews: int = Field(default=0, description="Positive review count")
    negative_reviews: int = Field(default=0, description="Negative review count")


class GameUpdate(BaseModel):
    """Schema for updating a game"""
    
    name: Optional[str] = Field(None, max_length=500)
    developer: Optional[str] = Field(None, max_length=500)
    publisher: Optional[str] = Field(None, max_length=500)
    release_date: Optional[date] = None
    is_free: Optional[bool] = None
    steamspy_owners_min: Optional[int] = None
    steamspy_owners_max: Optional[int] = None
    positive_reviews: Optional[int] = None
    negative_reviews: Optional[int] = None


class GameResponse(GameBase):
    """Schema for game response"""
    
    game_id: int = Field(..., description="Internal game ID")
    steamspy_owners_min: Optional[int] = None
    steamspy_owners_max: Optional[int] = None
    positive_reviews: int = 0
    negative_reviews: int = 0
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ========================================
# Extended Models (with relationships)
# ========================================


class TagSchema(BaseModel):
    """Tag schema"""
    
    tag_id: int
    tag_name: str
    
    model_config = ConfigDict(from_attributes=True)


class GenreSchema(BaseModel):
    """Genre schema"""
    
    genre_id: int
    genre_name: str
    
    model_config = ConfigDict(from_attributes=True)


class PlayerPriceFactSchema(BaseModel):
    """Player and price fact schema"""
    
    fact_id: int
    date_id: int
    concurrent_players_avg: Optional[int] = None
    concurrent_players_peak: Optional[int] = None
    avg_players_month: Optional[int] = None
    peak_players_month: Optional[int] = None
    current_price: Optional[float] = None
    original_price: Optional[float] = None
    discount_pct: Optional[float] = None
    is_discount_active: bool = False
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class GameDetailResponse(GameResponse):
    """Detailed game response with tags and recent data"""
    
    tags: List[TagSchema] = []
    recent_facts: List[PlayerPriceFactSchema] = Field(
        default=[],
        description="Recent player/price data (last 12 months)"
    )
    
    model_config = ConfigDict(from_attributes=True)


# ========================================
# List/Search Models
# ========================================


class GameListItem(BaseModel):
    """Minimal game info for list views"""
    
    game_id: int
    appid: int
    name: str
    developer: Optional[str] = None
    release_date: Optional[date] = None
    is_free: bool = False
    avg_recent_players: Optional[int] = Field(
        None,
        description="Average concurrent players (last 3 months)"
    )
    current_price: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)


class GameListResponse(BaseModel):
    """Paginated game list response"""
    
    games: List[GameListItem]
    total: int = Field(..., description="Total number of games matching criteria")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")


class GameSearchQuery(BaseModel):
    """Search query parameters"""
    
    query: Optional[str] = Field(None, description="Search query (name, developer, publisher)")
    genre: Optional[str] = Field(None, description="Filter by genre")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    is_free: Optional[bool] = Field(None, description="Filter by free/paid")
    min_players: Optional[int] = Field(None, description="Minimum average players")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(30, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(
        "name",
        description="Sort field (name, release_date, avg_players, price)"
    )
    sort_order: Optional[str] = Field("asc", description="Sort order (asc, desc)")
