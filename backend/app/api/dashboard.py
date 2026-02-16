"""
Dashboard API Endpoints
Summary metrics and aggregated data for dashboard
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, date

from app.db.session import get_session
from app.db.repositories.dashboard_repo import DashboardRepository
from app.schemas.dashboard import (
    DashboardResponse,
    DashboardSummary,
    KPICard,
    TopGamesResponse,
    TopGameItem,
    GenreDistributionResponse,
    GenreDistribution,
    AnalysisSummaryResponse,
    AnalysisSummaryItem,
    TimeSeriesResponse,
    TimeSeriesData,
    TimeSeriesPoint,
)

router = APIRouter()


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Get dashboard summary metrics",
)
async def get_dashboard_summary(
    session: AsyncSession = Depends(get_session),
):
    """
    Get summary metrics for the dashboard.
    
    **Returns:**
    - Total games in database
    - Total fact records
    - Average concurrent players
    - Active discount count
    - Average discount percentage
    - Latest data date
    - Key Performance Indicators (KPIs)
    """
    metrics = await DashboardRepository.get_summary_metrics(session)
    
    # Create KPI cards
    kpis = [
        KPICard(
            title="Total Games",
            value=metrics["total_games"],
            format="number",
        ),
        KPICard(
            title="Avg Concurrent Players",
            value=metrics["avg_concurrent_players"],
            format="number",
        ),
        KPICard(
            title="Active Discounts",
            value=metrics["active_discount_count"],
            format="number",
        ),
        KPICard(
            title="Avg Discount",
            value=f"{metrics['avg_discount_pct']:.1f}%",
            format="percentage",
        ),
    ]
    
    return DashboardSummary(
        total_games=metrics["total_games"],
        total_facts=metrics["total_facts"],
        avg_concurrent_players=metrics["avg_concurrent_players"],
        active_discount_count=metrics["active_discount_count"],
        avg_discount_pct=metrics["avg_discount_pct"],
        latest_data_date=metrics["latest_data_date"],
        kpis=kpis,
    )


@router.get(
    "/top-games",
    response_model=TopGamesResponse,
    summary="Get top games by various metrics",
)
async def get_top_games(
    limit: int = Query(10, ge=1, le=50, description="Number of games per category"),
    session: AsyncSession = Depends(get_session),
):
    """
    Get top games by player count, growth rate, and discount percentage.
    
    **Parameters:**
    - `limit`: Number of games to return in each category
    
    **Returns:**
    - Top games by concurrent players
    - Top games by player growth
    - Top discounted games
    """
    # Get top by players
    top_by_players_data = await DashboardRepository.get_top_games_by_players(
        session, limit
    )
    top_by_players = [
        TopGameItem(
            game_id=game.game_id,
            appid=game.appid,
            name=game.name,
            metric_value=value,
            metric_name="avg_players",
        )
        for game, value in top_by_players_data
    ]
    
    # Get top by growth
    top_by_growth_data = await DashboardRepository.get_top_games_by_growth(
        session, limit
    )
    top_by_growth = [
        TopGameItem(
            game_id=game.game_id,
            appid=game.appid,
            name=game.name,
            metric_value=value,
            metric_name="growth_pct",
        )
        for game, value in top_by_growth_data
    ]
    
    # Get top discounted
    top_discounted_data = await DashboardRepository.get_top_discounted_games(
        session, limit
    )
    top_discounted = [
        TopGameItem(
            game_id=game.game_id,
            appid=game.appid,
            name=game.name,
            metric_value=value,
            metric_name="discount_pct",
        )
        for game, value in top_discounted_data
    ]
    
    return TopGamesResponse(
        top_by_players=top_by_players,
        top_by_growth=top_by_growth,
        top_discounted=top_discounted,
        limit=limit,
    )


@router.get(
    "/genre-distribution",
    response_model=GenreDistributionResponse,
    summary="Get genre distribution",
)
async def get_genre_distribution(
    session: AsyncSession = Depends(get_session),
):
    """
    Get distribution of games across genres with metrics.
    
    **Returns:**
    - Genre name
    - Number of games in each genre
    - Average players per genre
    - Average price per genre
    - Total players per genre
    """
    distributions_data = await DashboardRepository.get_genre_distribution(session)
    
    distributions = [
        GenreDistribution(**data)
        for data in distributions_data
    ]
    
    return GenreDistributionResponse(
        distributions=distributions,
        total_genres=len(distributions),
    )


@router.get(
    "/analysis-summary",
    response_model=AnalysisSummaryResponse,
    summary="Get analysis summary",
)
async def get_analysis_summary(
    session: AsyncSession = Depends(get_session),
):
    """
    Get summary of all analyses performed.
    
    **Returns:**
    - Count of each analysis type
    - Last execution time for each type
    """
    summaries_data = await DashboardRepository.get_analysis_summary(session)
    
    analyses = [
        AnalysisSummaryItem(**data)
        for data in summaries_data
    ]
    
    return AnalysisSummaryResponse(
        analyses=analyses,
        total_analyses=sum(a.count for a in analyses),
    )


@router.get(
    "/time-series/players",
    response_model=TimeSeriesResponse,
    summary="Get player count time series",
)
async def get_player_time_series(
    start_date: Optional[date] = Query(
        None,
        description="Start date (defaults to 1 year ago)"
    ),
    end_date: Optional[date] = Query(
        None,
        description="End date (defaults to today)"
    ),
    game_id: Optional[int] = Query(
        None,
        description="Filter by specific game"
    ),
    session: AsyncSession = Depends(get_session),
):
    """
    Get time series data for player counts.
    
    **Parameters:**
    - `start_date`: Start date for time series
    - `end_date`: End date for time series
    - `game_id`: Optional game ID to filter
    
    **Returns:**
    - Time series data points
    - Date range covered
    """
    if not start_date:
        start_date = datetime.utcnow().date() - timedelta(days=365)
    if not end_date:
        end_date = datetime.utcnow().date()
    
    data = await DashboardRepository.get_time_series_players(
        session,
        start_date=start_date,
        end_date=end_date,
        game_id=game_id,
    )
    
    points = [
        TimeSeriesPoint(date=d["date"], value=d["value"])
        for d in data
    ]
    
    series_name = "Average Concurrent Players"
    if game_id:
        series_name += f" (Game {game_id})"
    
    return TimeSeriesResponse(
        series=[
            TimeSeriesData(
                series_name=series_name,
                data=points,
            )
        ],
        date_range={
            "start_date": start_date,
            "end_date": end_date,
        },
    )


@router.get(
    "/",
    response_model=DashboardResponse,
    summary="Get comprehensive dashboard data",
)
async def get_dashboard(
    session: AsyncSession = Depends(get_session),
):
    """
    Get comprehensive dashboard data in a single request.
    
    **Returns:**
    - Summary metrics
    - Top games by various metrics
    - Genre distribution
    - Recent analyses
    - Generation timestamp
    """
    # Get all dashboard data
    summary_metrics = await DashboardRepository.get_summary_metrics(session)
    
    # Create summary
    kpis = [
        KPICard(title="Total Games", value=summary_metrics["total_games"], format="number"),
        KPICard(title="Avg Players", value=summary_metrics["avg_concurrent_players"], format="number"),
        KPICard(title="Active Discounts", value=summary_metrics["active_discount_count"], format="number"),
    ]
    
    summary = DashboardSummary(
        total_games=summary_metrics["total_games"],
        total_facts=summary_metrics["total_facts"],
        avg_concurrent_players=summary_metrics["avg_concurrent_players"],
        active_discount_count=summary_metrics["active_discount_count"],
        avg_discount_pct=summary_metrics["avg_discount_pct"],
        latest_data_date=summary_metrics["latest_data_date"],
        kpis=kpis,
    )
    
    # Get top games
    top_by_players_data = await DashboardRepository.get_top_games_by_players(session, 10)
    top_by_growth_data = await DashboardRepository.get_top_games_by_growth(session, 10)
    top_discounted_data = await DashboardRepository.get_top_discounted_games(session, 10)
    
    top_games = TopGamesResponse(
        top_by_players=[
            TopGameItem(
                game_id=g.game_id,
                appid=g.appid,
                name=g.name,
                metric_value=v,
                metric_name="avg_players",
            )
            for g, v in top_by_players_data
        ],
        top_by_growth=[
            TopGameItem(
                game_id=g.game_id,
                appid=g.appid,
                name=g.name,
                metric_value=v,
                metric_name="growth_pct",
            )
            for g, v in top_by_growth_data
        ],
        top_discounted=[
            TopGameItem(
                game_id=g.game_id,
                appid=g.appid,
                name=g.name,
                metric_value=v,
                metric_name="discount_pct",
            )
            for g, v in top_discounted_data
        ],
    )
    
    # Get genre distribution
    distributions_data = await DashboardRepository.get_genre_distribution(session)
    genre_distribution = GenreDistributionResponse(
        distributions=[GenreDistribution(**d) for d in distributions_data],
        total_genres=len(distributions_data),
    )
    
    # Get analysis summary
    analyses_data = await DashboardRepository.get_analysis_summary(session)
    recent_analyses = [AnalysisSummaryItem(**a) for a in analyses_data]
    
    return DashboardResponse(
        summary=summary,
        top_games=top_games,
        genre_distribution=genre_distribution,
        recent_analyses=recent_analyses,
        generated_at=datetime.utcnow(),
    )
