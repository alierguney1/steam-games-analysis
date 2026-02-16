"""
Analytical Utilities Module
Common helper functions for analysis modules
"""

from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import FactPlayerPrice, DimGame, DimDate, DimGenre


async def fetch_player_price_data(
    session: AsyncSession,
    game_ids: Optional[List[int]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    genre_id: Optional[int] = None,
) -> pd.DataFrame:
    """
    Fetch player and price data from fact table as DataFrame
    
    Args:
        session: Database session
        game_ids: Optional list of game_ids to filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        genre_id: Optional genre filter
    
    Returns:
        DataFrame with columns: game_id, appid, game_name, date, 
                                avg_players, peak_players, current_price, 
                                discount_pct, is_discount_active
    """
    query = (
        select(
            FactPlayerPrice.game_id,
            DimGame.appid,
            DimGame.name.label("game_name"),
            DimDate.full_date.label("date"),
            FactPlayerPrice.avg_players_month.label("avg_players"),
            FactPlayerPrice.peak_players_month.label("peak_players"),
            FactPlayerPrice.current_price,
            FactPlayerPrice.discount_pct,
            FactPlayerPrice.is_discount_active,
            DimGenre.genre_name,
        )
        .join(DimGame, FactPlayerPrice.game_id == DimGame.game_id)
        .join(DimDate, FactPlayerPrice.date_id == DimDate.date_id)
        .outerjoin(DimGenre, FactPlayerPrice.genre_id == DimGenre.genre_id)
    )
    
    if game_ids:
        query = query.where(FactPlayerPrice.game_id.in_(game_ids))
    
    if start_date:
        query = query.where(DimDate.full_date >= start_date)
    
    if end_date:
        query = query.where(DimDate.full_date <= end_date)
    
    if genre_id:
        query = query.where(FactPlayerPrice.genre_id == genre_id)
    
    result = await session.execute(query)
    rows = result.all()
    
    # Convert to DataFrame
    df = pd.DataFrame(
        [
            {
                "game_id": r.game_id,
                "appid": r.appid,
                "game_name": r.game_name,
                "date": r.date,
                "avg_players": r.avg_players,
                "peak_players": r.peak_players,
                "current_price": float(r.current_price) if r.current_price else None,
                "discount_pct": float(r.discount_pct) if r.discount_pct else 0.0,
                "is_discount_active": r.is_discount_active,
                "genre_name": r.genre_name,
            }
            for r in rows
        ]
    )
    
    return df


def create_cohorts(
    df: pd.DataFrame,
    treatment_condition: callable,
    pre_period_months: int = 3,
    post_period_months: int = 3,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Create treatment and control cohorts for DiD analysis
    
    Args:
        df: Input DataFrame with game_id, date, and relevant metrics
        treatment_condition: Function that takes a row and returns True if treated
        pre_period_months: Number of months before treatment
        post_period_months: Number of months after treatment
    
    Returns:
        Tuple of (treatment_df, control_df)
    """
    df = df.copy()
    df["is_treatment"] = df.apply(treatment_condition, axis=1)
    
    treatment_df = df[df["is_treatment"] == True].copy()
    control_df = df[df["is_treatment"] == False].copy()
    
    return treatment_df, control_df


def identify_discount_events(
    df: pd.DataFrame, 
    min_discount_pct: float = 30.0,
    min_duration_days: int = 7,
) -> pd.DataFrame:
    """
    Identify significant discount events in the data
    
    Args:
        df: DataFrame with discount information
        min_discount_pct: Minimum discount percentage to consider
        min_duration_days: Minimum duration of discount in days
    
    Returns:
        DataFrame with discount events (game_id, start_date, end_date, discount_pct)
    """
    df = df.sort_values(["game_id", "date"])
    
    # Check required columns exist
    if "is_discount_active" not in df.columns or "discount_pct" not in df.columns:
        return pd.DataFrame(columns=["game_id", "start_date", "end_date", "discount_pct"])
    
    events = []
    current_event = None
    
    for _, row in df.iterrows():
        if row["is_discount_active"] and row["discount_pct"] >= min_discount_pct:
            if current_event is None or current_event["game_id"] != row["game_id"]:
                # Start new event
                current_event = {
                    "game_id": row["game_id"],
                    "start_date": row["date"],
                    "end_date": row["date"],
                    "discount_pct": row["discount_pct"],
                }
            else:
                # Continue current event
                current_event["end_date"] = row["date"]
                current_event["discount_pct"] = max(
                    current_event["discount_pct"], row["discount_pct"]
                )
        else:
            # Event ended, check if it meets duration criteria
            if current_event is not None:
                duration = (current_event["end_date"] - current_event["start_date"]).days
                if duration >= min_duration_days:
                    events.append(current_event)
                current_event = None
    
    # Check last event
    if current_event is not None:
        duration = (current_event["end_date"] - current_event["start_date"]).days
        if duration >= min_duration_days:
            events.append(current_event)
    
    return pd.DataFrame(events)


def calculate_churn_events(
    df: pd.DataFrame,
    player_threshold_pct: float = 0.5,
    lookback_months: int = 3,
) -> pd.DataFrame:
    """
    Calculate churn events for survival analysis
    
    A game is considered "churned" when player count drops below threshold_pct
    of its historical average over the lookback period.
    
    Args:
        df: DataFrame with game_id, date, avg_players
        player_threshold_pct: Percentage of historical average to trigger churn
        lookback_months: Number of months to calculate historical average
    
    Returns:
        DataFrame with churn events (game_id, churn_date, time_to_churn_months)
    """
    df = df.sort_values(["game_id", "date"])
    df["rolling_avg"] = df.groupby("game_id")["avg_players"].transform(
        lambda x: x.rolling(window=lookback_months, min_periods=1).mean()
    )
    
    churn_events = []
    
    for game_id in df["game_id"].unique():
        game_df = df[df["game_id"] == game_id].copy()
        
        # Skip if insufficient data
        if len(game_df) < lookback_months + 1:
            continue
        
        # Find first occurrence where players drop below threshold
        threshold = game_df["rolling_avg"].max() * player_threshold_pct
        churned = game_df[game_df["avg_players"] < threshold]
        
        if len(churned) > 0:
            churn_date = churned.iloc[0]["date"]
            first_date = game_df.iloc[0]["date"]
            
            # Calculate time to churn in months
            time_to_churn = (
                (churn_date.year - first_date.year) * 12 
                + (churn_date.month - first_date.month)
            )
            
            churn_events.append({
                "game_id": game_id,
                "churn_date": churn_date,
                "time_to_churn_months": time_to_churn,
                "churned": True,
            })
        else:
            # Game hasn't churned (censored)
            last_date = game_df.iloc[-1]["date"]
            first_date = game_df.iloc[0]["date"]
            
            time_observed = (
                (last_date.year - first_date.year) * 12 
                + (last_date.month - first_date.month)
            )
            
            churn_events.append({
                "game_id": game_id,
                "churn_date": None,
                "time_to_churn_months": time_observed,
                "churned": False,
            })
    
    return pd.DataFrame(churn_events)


def prepare_panel_data(
    df: pd.DataFrame,
    id_col: str = "game_id",
    time_col: str = "date",
) -> pd.DataFrame:
    """
    Prepare panel data structure for econometric analysis
    
    Args:
        df: Input DataFrame
        id_col: Column name for entity ID
        time_col: Column name for time dimension
    
    Returns:
        DataFrame with proper panel structure and time indexing
    """
    df = df.copy()
    
    # Ensure proper sorting
    df = df.sort_values([id_col, time_col])
    
    # Add time period index (0, 1, 2, ...)
    df["time_period"] = df.groupby(id_col).cumcount()
    
    # Add lagged variables (useful for DiD)
    for col in ["avg_players", "current_price", "discount_pct"]:
        if col in df.columns:
            df[f"{col}_lag1"] = df.groupby(id_col)[col].shift(1)
            df[f"{col}_lag2"] = df.groupby(id_col)[col].shift(2)
    
    return df


def validate_parallel_trends(
    treatment_df: pd.DataFrame,
    control_df: pd.DataFrame,
    outcome_col: str = "avg_players",
    pre_treatment_periods: int = 3,
) -> Dict[str, float]:
    """
    Validate parallel trends assumption for DiD
    
    Tests if treatment and control groups have similar trends before treatment.
    
    Args:
        treatment_df: Treatment group DataFrame
        control_df: Control group DataFrame
        outcome_col: Column name for outcome variable
        pre_treatment_periods: Number of pre-treatment periods to test
    
    Returns:
        Dictionary with test statistics and p-value
    """
    from scipy import stats
    
    # Calculate mean outcome by period for each group
    treatment_means = treatment_df.groupby("time_period")[outcome_col].mean()
    control_means = control_df.groupby("time_period")[outcome_col].mean()
    
    # Get pre-treatment periods
    pre_treatment = treatment_means.index < pre_treatment_periods
    treatment_pre = treatment_means[pre_treatment].values
    control_pre = control_means[pre_treatment].values
    
    # Calculate slopes
    treatment_slope = np.polyfit(range(len(treatment_pre)), treatment_pre, 1)[0]
    control_slope = np.polyfit(range(len(control_pre)), control_pre, 1)[0]
    
    # Test if slopes are significantly different
    slope_diff = abs(treatment_slope - control_slope)
    
    # Calculate correlation (additional metric)
    if len(treatment_pre) == len(control_pre):
        correlation, p_value = stats.pearsonr(treatment_pre, control_pre)
    else:
        correlation, p_value = None, None
    
    return {
        "treatment_slope": treatment_slope,
        "control_slope": control_slope,
        "slope_difference": slope_diff,
        "correlation": correlation,
        "p_value": p_value,
        "parallel_trends_valid": slope_diff < 0.1 * abs(treatment_slope),  # 10% threshold
    }
