"""
Application Configuration
Pydantic Settings for environment variable management
"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Project metadata
    PROJECT_NAME: str = "Steam Analytics API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development")
    
    # API Configuration
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    
    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://steam_user:steam_password@localhost:5432/steam_analytics"
    )
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"]
    )
    
    # External API Configuration
    STEAMSPY_API_URL: str = Field(default="https://steamspy.com/api.php")
    STEAM_STORE_API_URL: str = Field(default="https://store.steampowered.com/api/appdetails")
    STEAMCHARTS_BASE_URL: str = Field(default="https://steamcharts.com")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = Field(default=1)
    RATE_LIMIT_PERIOD: float = Field(default=1.0)
    
    # Scraping Configuration
    USER_AGENT: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    REQUEST_TIMEOUT: int = Field(default=30)
    MAX_RETRIES: int = Field(default=3)
    RETRY_BACKOFF: float = Field(default=2.0)
    
    # Scheduler Configuration
    SCHEDULER_TIMEZONE: str = Field(default="UTC")
    DAILY_ETL_HOUR: int = Field(default=3)
    WEEKLY_ETL_DAY: str = Field(default="monday")
    MONTHLY_ANALYSIS_DAY: int = Field(default=1)
    
    # Analytics Configuration
    DID_PRE_PERIODS: int = Field(default=6, description="DiD pre-treatment periods in months")
    DID_POST_PERIODS: int = Field(default=3, description="DiD post-treatment periods in months")
    MIN_DISCOUNT_PCT: float = Field(default=25.0, description="Minimum discount % for treatment group")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()
