"""schemas package"""

from app.schemas.game import (
    GameBase,
    GameCreate,
    GameUpdate,
    GameResponse,
    GameDetailResponse,
    GameListItem,
    GameListResponse,
    GameSearchQuery,
    TagSchema,
    GenreSchema,
    PlayerPriceFactSchema,
)

from app.schemas.analytics import (
    DiDRequest,
    DiDResponse,
    SurvivalRequest,
    SurvivalResponse,
    ElasticityRequest,
    ElasticityResponse,
    AnalysisListItem,
    AnalysisListResponse,
)

from app.schemas.ingestion import (
    IngestionTriggerRequest,
    IngestionJobResponse,
    IngestionStatusResponse,
    IngestionStats,
    IngestionStatus,
    DataSource,
    DataQualityMetrics,
    DataQualityResponse,
)

from app.schemas.dashboard import (
    DashboardSummary,
    DashboardResponse,
    KPICard,
    TimeSeriesPoint,
    TimeSeriesData,
    TimeSeriesResponse,
    TopGameItem,
    TopGamesResponse,
    GenreDistribution,
    GenreDistributionResponse,
    AnalysisSummaryItem,
    AnalysisSummaryResponse,
)

__all__ = [
    # Game schemas
    "GameBase",
    "GameCreate",
    "GameUpdate",
    "GameResponse",
    "GameDetailResponse",
    "GameListItem",
    "GameListResponse",
    "GameSearchQuery",
    "TagSchema",
    "GenreSchema",
    "PlayerPriceFactSchema",
    # Analytics schemas
    "DiDRequest",
    "DiDResponse",
    "SurvivalRequest",
    "SurvivalResponse",
    "ElasticityRequest",
    "ElasticityResponse",
    "AnalysisListItem",
    "AnalysisListResponse",
    # Ingestion schemas
    "IngestionTriggerRequest",
    "IngestionJobResponse",
    "IngestionStatusResponse",
    "IngestionStats",
    "IngestionStatus",
    "DataSource",
    "DataQualityMetrics",
    "DataQualityResponse",
    # Dashboard schemas
    "DashboardSummary",
    "DashboardResponse",
    "KPICard",
    "TimeSeriesPoint",
    "TimeSeriesData",
    "TimeSeriesResponse",
    "TopGameItem",
    "TopGamesResponse",
    "GenreDistribution",
    "GenreDistributionResponse",
    "AnalysisSummaryItem",
    "AnalysisSummaryResponse",
]

