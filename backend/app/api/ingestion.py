"""
Ingestion API Endpoints
Manual ETL trigger and status monitoring
"""

from typing import Optional
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
import uuid

from app.db.session import get_session
from app.db.models import DimGame, FactPlayerPrice
from app.schemas.ingestion import (
    IngestionTriggerRequest,
    IngestionJobResponse,
    IngestionStatusResponse,
    IngestionStats,
    IngestionStatus,
    DataQualityMetrics,
    DataQualityResponse,
)

router = APIRouter()


# In-memory job tracking (in production, use Redis or database)
active_jobs = {}


async def run_ingestion_job(
    job_id: str,
    appids: Optional[list[int]],
    sources: list[str],
    force_refresh: bool,
):
    """Background task for running ingestion"""
    try:
        active_jobs[job_id]["status"] = IngestionStatus.RUNNING
        
        # Simulate ingestion process
        # In production, this would call the actual ingestion modules
        import asyncio
        await asyncio.sleep(2)  # Simulate work
        
        # Update job status
        active_jobs[job_id]["status"] = IngestionStatus.COMPLETED
        active_jobs[job_id]["completed_at"] = datetime.utcnow()
        active_jobs[job_id]["stats"] = IngestionStats(
            games_fetched=len(appids) if appids else 100,
            games_created=5,
            games_updated=95,
            facts_created=500,
            tags_created=20,
            genres_created=3,
        )
        
    except Exception as e:
        active_jobs[job_id]["status"] = IngestionStatus.FAILED
        active_jobs[job_id]["error_message"] = str(e)
        active_jobs[job_id]["completed_at"] = datetime.utcnow()


@router.post(
    "/trigger",
    response_model=IngestionJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger manual ingestion",
)
async def trigger_ingestion(
    request: IngestionTriggerRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """
    Manually trigger data ingestion process.
    
    **Parameters:**
    - `appids`: List of specific Steam App IDs to fetch (fetches all if not provided)
    - `sources`: Data sources to fetch from (steamspy, steamcharts, steam_store)
    - `force_refresh`: Force refresh even if recent data exists
    
    **Returns:**
    - Job ID for tracking the ingestion progress
    - Job status (pending, running, completed, failed)
    
    The ingestion runs in the background. Use `/ingestion/status/{job_id}` to check progress.
    """
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Initialize job tracking
    active_jobs[job_id] = {
        "job_id": job_id,
        "status": IngestionStatus.PENDING,
        "started_at": datetime.utcnow(),
        "completed_at": None,
        "stats": None,
        "error_message": None,
    }
    
    # Schedule background task
    background_tasks.add_task(
        run_ingestion_job,
        job_id,
        request.appids,
        [s.value for s in request.sources],
        request.force_refresh,
    )
    
    return IngestionJobResponse(**active_jobs[job_id])


@router.get(
    "/status/{job_id}",
    response_model=IngestionJobResponse,
    summary="Get ingestion job status",
)
async def get_job_status(
    job_id: str,
):
    """
    Get the status of a specific ingestion job.
    
    **Returns:**
    - Job status and progress
    - Statistics (if completed)
    - Error message (if failed)
    """
    if job_id not in active_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    
    job = active_jobs[job_id]
    
    # Calculate duration
    duration = None
    if job["completed_at"]:
        duration = (job["completed_at"] - job["started_at"]).total_seconds()
    
    return IngestionJobResponse(
        **job,
        duration_seconds=duration,
    )


@router.get(
    "/status",
    response_model=IngestionStatusResponse,
    summary="Get overall ingestion status",
)
async def get_ingestion_status(
    session: AsyncSession = Depends(get_session),
):
    """
    Get overall status of the ingestion pipeline.
    
    **Returns:**
    - Last full ETL timestamp
    - Last price sync timestamp
    - Total games and facts in database
    - Recent jobs history
    - Whether ingestion is currently running
    """
    # Get database statistics
    total_games_query = select(func.count()).select_from(DimGame)
    total_games_result = await session.execute(total_games_query)
    total_games = total_games_result.scalar() or 0
    
    total_facts_query = select(func.count()).select_from(FactPlayerPrice)
    total_facts_result = await session.execute(total_facts_query)
    total_facts = total_facts_result.scalar() or 0
    
    # Get recent jobs (last 10)
    recent_jobs_list = []
    for job_id, job_data in list(active_jobs.items())[-10:]:
        duration = None
        if job_data["completed_at"]:
            duration = (
                job_data["completed_at"] - job_data["started_at"]
            ).total_seconds()
        
        recent_jobs_list.append(
            IngestionJobResponse(**job_data, duration_seconds=duration)
        )
    
    # Check if any job is currently running
    is_running = any(
        job["status"] == IngestionStatus.RUNNING
        for job in active_jobs.values()
    )
    
    # Get last completed ETL time
    last_full_etl = None
    for job in reversed(list(active_jobs.values())):
        if job["status"] == IngestionStatus.COMPLETED:
            last_full_etl = job["completed_at"]
            break
    
    return IngestionStatusResponse(
        last_full_etl=last_full_etl,
        last_price_sync=last_full_etl,  # Simplified
        total_games=total_games,
        total_facts=total_facts,
        recent_jobs=recent_jobs_list,
        is_running=is_running,
    )


@router.get(
    "/data-quality",
    response_model=DataQualityResponse,
    summary="Get data quality metrics",
)
async def get_data_quality(
    session: AsyncSession = Depends(get_session),
):
    """
    Get data quality metrics and recommendations.
    
    **Returns:**
    - Games with complete vs incomplete data
    - Date range coverage
    - Average facts per game
    - Recommendations for data improvement
    """
    # Total games
    total_games_query = select(func.count()).select_from(DimGame)
    total_games_result = await session.execute(total_games_query)
    total_games = total_games_result.scalar() or 0
    
    # Games with price data
    games_with_price_query = (
        select(func.count(func.distinct(FactPlayerPrice.game_id)))
        .select_from(FactPlayerPrice)
        .where(FactPlayerPrice.current_price.isnot(None))
    )
    games_with_price_result = await session.execute(games_with_price_query)
    games_with_price_data = games_with_price_result.scalar() or 0
    
    # Games with player data
    games_with_player_query = (
        select(func.count(func.distinct(FactPlayerPrice.game_id)))
        .select_from(FactPlayerPrice)
        .where(FactPlayerPrice.concurrent_players_avg.isnot(None))
    )
    games_with_player_result = await session.execute(games_with_player_query)
    games_with_player_data = games_with_player_result.scalar() or 0
    
    # Games missing metadata
    games_missing_metadata_query = (
        select(func.count())
        .select_from(DimGame)
        .where(
            (DimGame.developer.is_(None))
            | (DimGame.publisher.is_(None))
            | (DimGame.release_date.is_(None))
        )
    )
    games_missing_result = await session.execute(games_missing_metadata_query)
    games_missing_metadata = games_missing_result.scalar() or 0
    
    # Date range
    from app.db.models import DimDate
    
    date_range_query = select(
        func.min(DimDate.full_date),
        func.max(DimDate.full_date),
    ).select_from(DimDate)
    date_range_result = await session.execute(date_range_query)
    date_range = date_range_result.first()
    oldest_fact_date = date_range[0] if date_range else None
    newest_fact_date = date_range[1] if date_range else None
    
    # Average facts per game
    avg_facts_query = (
        select(func.count() / func.count(func.distinct(FactPlayerPrice.game_id)))
        .select_from(FactPlayerPrice)
    )
    avg_facts_result = await session.execute(avg_facts_query)
    avg_facts_per_game = float(avg_facts_result.scalar() or 0)
    
    # Generate recommendations
    recommendations = []
    
    if games_missing_metadata > 0:
        recommendations.append(
            f"{games_missing_metadata} games are missing metadata (developer, publisher, or release date)"
        )
    
    if total_games > 0:
        price_coverage = (games_with_price_data / total_games) * 100
        if price_coverage < 80:
            recommendations.append(
                f"Only {price_coverage:.1f}% of games have price data. Consider running Steam Store ingestion."
            )
        
        player_coverage = (games_with_player_data / total_games) * 100
        if player_coverage < 80:
            recommendations.append(
                f"Only {player_coverage:.1f}% of games have player data. Consider running SteamCharts ingestion."
            )
    
    if avg_facts_per_game < 6:
        recommendations.append(
            f"Average of {avg_facts_per_game:.1f} facts per game. Consider running historical data ingestion."
        )
    
    metrics = DataQualityMetrics(
        total_games=total_games,
        games_with_price_data=games_with_price_data,
        games_with_player_data=games_with_player_data,
        games_missing_metadata=games_missing_metadata,
        oldest_fact_date=oldest_fact_date,
        newest_fact_date=newest_fact_date,
        avg_facts_per_game=avg_facts_per_game,
    )
    
    return DataQualityResponse(
        metrics=metrics,
        recommendations=recommendations,
    )
