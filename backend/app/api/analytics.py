"""
Analytics API Endpoints
DiD, Survival, and Elasticity analysis endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
from datetime import datetime

from app.db.session import get_session
from app.db.repositories.analysis_repo import AnalysisRepository
from app.db.repositories.game_repo import GameRepository
from app.db.models import AnalysisTypeEnum, FactPlayerPrice, DimDate
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
from app.analysis.did_model import run_did_analysis
from app.analysis.survival import run_survival_analysis
from app.analysis.elasticity import run_elasticity_analysis
from sqlalchemy import select

router = APIRouter()


async def get_game_data_for_analysis(
    session: AsyncSession,
    game_id: int,
) -> pd.DataFrame:
    """Helper function to get game data as DataFrame"""
    query = (
        select(FactPlayerPrice, DimDate.full_date)
        .join(DimDate)
        .where(FactPlayerPrice.game_id == game_id)
        .order_by(DimDate.full_date)
    )
    
    result = await session.execute(query)
    rows = result.all()
    
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for game {game_id}",
        )
    
    data = []
    for fact, date in rows:
        data.append({
            "game_id": fact.game_id,
            "date": date,
            "avg_players": fact.concurrent_players_avg,
            "current_price": float(fact.current_price) if fact.current_price else None,
            "discount_pct": float(fact.discount_pct) if fact.discount_pct else 0.0,
            "is_discount_active": fact.is_discount_active,
        })
    
    return pd.DataFrame(data)


@router.post(
    "/did",
    response_model=DiDResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run Difference-in-Differences analysis",
)
async def run_did(
    request: DiDRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """
    Run Difference-in-Differences (DiD) analysis to measure causal effect
    of discount events on player counts.
    
    **Parameters:**
    - `treatment_game_id`: Game that received the discount (treatment)
    - `control_game_ids`: Games that did not receive discount (control group)
    - `pre_periods`: Number of months before discount
    - `post_periods`: Number of months after discount
    - `discount_threshold`: Minimum discount percentage to consider
    
    **Returns:**
    - DiD estimation results including ATT (Average Treatment Effect on Treated)
    - Parallel trends test results
    - P-values and confidence intervals
    """
    # Verify treatment game exists
    treatment_game = await GameRepository.get_game_by_id(
        session, request.treatment_game_id
    )
    if not treatment_game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Treatment game {request.treatment_game_id} not found",
        )
    
    # Get treatment data
    treatment_df = await get_game_data_for_analysis(session, request.treatment_game_id)
    
    # Get control data (simplified - using first control game or auto-select)
    if request.control_game_ids:
        control_game_id = request.control_game_ids[0]
    else:
        # Auto-select a control game (simplified - would need better matching in production)
        control_game_id = request.treatment_game_id + 1  # Placeholder
    
    control_df = await get_game_data_for_analysis(session, control_game_id)
    
    # Run DiD analysis
    try:
        results = run_did_analysis(treatment_df, control_df)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"DiD analysis failed: {str(e)}",
        )
    
    # Store results in database
    parameters = {
        "treatment_game_id": request.treatment_game_id,
        "control_game_ids": request.control_game_ids or [control_game_id],
        "pre_periods": request.pre_periods,
        "post_periods": request.post_periods,
        "discount_threshold": request.discount_threshold,
    }
    
    analysis_result = await AnalysisRepository.create_result(
        session=session,
        analysis_type=AnalysisTypeEnum.DID,
        parameters=parameters,
        results=results,
        game_id=request.treatment_game_id,
    )
    
    return DiDResponse(
        result_id=analysis_result.result_id,
        analysis_type=analysis_result.analysis_type,
        game_id=analysis_result.game_id,
        parameters=analysis_result.parameters,
        results=analysis_result.results,
        executed_at=analysis_result.executed_at,
        model_version=analysis_result.model_version,
    )


@router.post(
    "/survival",
    response_model=SurvivalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run Survival analysis",
)
async def run_survival(
    request: SurvivalRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Run Survival analysis (Kaplan-Meier and Cox Proportional Hazards)
    to model player retention and churn.
    
    **Parameters:**
    - `game_ids`: Specific games to analyze (optional)
    - `genre`: Filter by genre (optional)
    - `churn_threshold_pct`: Player decline threshold for churn definition
    - `groupby_col`: Column to group by for comparison
    
    **Returns:**
    - Kaplan-Meier survival curves
    - Cox PH hazard ratios
    - Retention metrics
    - Median time to churn
    """
    # Get data for analysis
    query = select(FactPlayerPrice, DimDate.full_date).join(DimDate)
    
    if request.game_ids:
        query = query.where(FactPlayerPrice.game_id.in_(request.game_ids))
    
    result = await session.execute(query)
    rows = result.all()
    
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No data found for the specified criteria",
        )
    
    # Convert to DataFrame
    data = []
    for fact, date in rows:
        data.append({
            "game_id": fact.game_id,
            "date": date,
            "avg_players": fact.concurrent_players_avg,
        })
    
    df = pd.DataFrame(data)
    
    # Run survival analysis
    try:
        results = run_survival_analysis(
            df,
            churn_threshold_pct=request.churn_threshold_pct,
            groupby_col=request.groupby_col,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Survival analysis failed: {str(e)}",
        )
    
    # Store results
    parameters = {
        "game_ids": request.game_ids,
        "genre": request.genre,
        "churn_threshold_pct": request.churn_threshold_pct,
        "groupby_col": request.groupby_col,
    }
    
    analysis_result = await AnalysisRepository.create_result(
        session=session,
        analysis_type=AnalysisTypeEnum.KAPLAN_MEIER,
        parameters=parameters,
        results=results,
    )
    
    return SurvivalResponse(
        result_id=analysis_result.result_id,
        analysis_type=analysis_result.analysis_type,
        genre_id=analysis_result.genre_id,
        parameters=analysis_result.parameters,
        results=analysis_result.results,
        executed_at=analysis_result.executed_at,
        model_version=analysis_result.model_version,
    )


@router.post(
    "/elasticity",
    response_model=ElasticityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run Price Elasticity analysis",
)
async def run_elasticity(
    request: ElasticityRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Run Price Elasticity analysis to calculate demand elasticity
    and optimal pricing recommendations.
    
    **Parameters:**
    - `genre`: Analyze specific genre (optional)
    - `method`: Regression method (log_log, linear, arc_elasticity)
    - `group_by`: Group elasticity by column
    - `min_price`, `max_price`: Price range filters
    
    **Returns:**
    - Elasticity coefficients
    - Optimal pricing recommendations
    - Genre-specific elasticity heatmaps
    """
    # Get data for analysis
    query = (
        select(FactPlayerPrice)
        .where(FactPlayerPrice.current_price.isnot(None))
        .where(FactPlayerPrice.concurrent_players_avg.isnot(None))
    )
    
    if request.min_price:
        query = query.where(FactPlayerPrice.current_price >= request.min_price)
    if request.max_price:
        query = query.where(FactPlayerPrice.current_price <= request.max_price)
    
    result = await session.execute(query)
    rows = result.scalars().all()
    
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pricing data found for the specified criteria",
        )
    
    # Convert to DataFrame
    data = []
    for fact in rows:
        data.append({
            "game_id": fact.game_id,
            "current_price": float(fact.current_price),
            "avg_players": fact.concurrent_players_avg,
        })
    
    df = pd.DataFrame(data)
    
    # Run elasticity analysis
    try:
        results = run_elasticity_analysis(
            df,
            method=request.method,
            group_by=request.group_by,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Elasticity analysis failed: {str(e)}",
        )
    
    # Store results
    parameters = {
        "genre": request.genre,
        "method": request.method,
        "group_by": request.group_by,
        "min_price": request.min_price,
        "max_price": request.max_price,
    }
    
    analysis_result = await AnalysisRepository.create_result(
        session=session,
        analysis_type=AnalysisTypeEnum.ELASTICITY,
        parameters=parameters,
        results=results,
    )
    
    return ElasticityResponse(
        result_id=analysis_result.result_id,
        analysis_type=analysis_result.analysis_type,
        genre_id=analysis_result.genre_id,
        parameters=analysis_result.parameters,
        results=analysis_result.results,
        executed_at=analysis_result.executed_at,
        model_version=analysis_result.model_version,
    )


@router.get(
    "/results",
    response_model=AnalysisListResponse,
    summary="List analysis results",
)
async def list_analysis_results(
    analysis_type: Optional[str] = Query(None, description="Filter by analysis type"),
    game_id: Optional[int] = Query(None, description="Filter by game ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_session),
):
    """
    List analysis results with optional filtering and pagination.
    
    **Filters:**
    - `analysis_type`: Filter by type (did, kaplan_meier, cox_ph, elasticity)
    - `game_id`: Filter by game ID
    """
    # Parse analysis type
    type_enum = None
    if analysis_type:
        try:
            type_enum = AnalysisTypeEnum(analysis_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid analysis type: {analysis_type}",
            )
    
    results = await AnalysisRepository.get_latest_results(
        session=session,
        analysis_type=type_enum,
        game_id=game_id,
        limit=page_size,
    )
    
    # Get total count
    # (Simplified - would need a separate count query in production)
    total = len(results)
    
    items = [
        AnalysisListItem(
            result_id=r.result_id,
            analysis_type=r.analysis_type,
            game_id=r.game_id,
            genre_id=r.genre_id,
            executed_at=r.executed_at,
            model_version=r.model_version,
        )
        for r in results
    ]
    
    return AnalysisListResponse(
        results=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/results/{result_id}",
    summary="Get analysis result by ID",
)
async def get_analysis_result(
    result_id: int,
    session: AsyncSession = Depends(get_session),
):
    """
    Get detailed analysis result by ID.
    
    Returns the complete analysis result including parameters and results.
    """
    result = await AnalysisRepository.get_result_by_id(session, result_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis result {result_id} not found",
        )
    
    return {
        "result_id": result.result_id,
        "analysis_type": result.analysis_type,
        "game_id": result.game_id,
        "genre_id": result.genre_id,
        "parameters": result.parameters,
        "results": result.results,
        "executed_at": result.executed_at,
        "model_version": result.model_version,
    }
