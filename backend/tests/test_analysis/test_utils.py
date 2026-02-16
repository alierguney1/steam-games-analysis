"""
Tests for Analysis Utilities Module
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.analysis.utils import (
    create_cohorts,
    identify_discount_events,
    calculate_churn_events,
    prepare_panel_data,
    validate_parallel_trends,
)


@pytest.fixture
def sample_df():
    """Create sample DataFrame for testing"""
    np.random.seed(42)
    
    data = []
    start_date = datetime(2024, 1, 1)
    
    for game_id in [1, 2]:
        for i in range(12):
            date = start_date + timedelta(days=30*i)
            
            data.append({
                "game_id": game_id,
                "date": date,
                "avg_players": 1000 + np.random.normal(0, 100),
                "current_price": 20.0 - (5.0 if (game_id == 1 and i >= 6) else 0),
                "discount_pct": 25.0 if (game_id == 1 and i >= 6) else 0.0,
                "is_discount_active": (game_id == 1 and i >= 6),
            })
    
    return pd.DataFrame(data)


def test_create_cohorts(sample_df):
    """Test cohort creation"""
    # Define treatment condition: games with any discount
    def treatment_condition(row):
        return row["is_discount_active"]
    
    treatment_df, control_df = create_cohorts(
        sample_df,
        treatment_condition=treatment_condition,
    )
    
    assert len(treatment_df) > 0
    assert len(control_df) > 0
    assert all(treatment_df["is_treatment"] == True)
    assert all(control_df["is_treatment"] == False)


def test_identify_discount_events(sample_df):
    """Test discount event identification"""
    events = identify_discount_events(
        sample_df,
        min_discount_pct=20.0,
        min_duration_days=7,
    )
    
    assert len(events) > 0
    assert "game_id" in events.columns
    assert "start_date" in events.columns
    assert "end_date" in events.columns
    assert "discount_pct" in events.columns
    
    # Game 1 should have a discount event
    game1_events = events[events["game_id"] == 1]
    assert len(game1_events) > 0


def test_identify_discount_events_min_duration():
    """Test discount event filtering by minimum duration"""
    # Create data with short discount periods
    data = []
    for i in range(10):
        data.append({
            "game_id": 1,
            "date": datetime(2024, 1, 1) + timedelta(days=i),
            "discount_pct": 30.0 if 3 <= i <= 5 else 0.0,  # 3-day discount
            "is_discount_active": 3 <= i <= 5,
        })
    
    df = pd.DataFrame(data)
    
    # With 7-day minimum, should find no events
    events = identify_discount_events(df, min_duration_days=7)
    assert len(events) == 0
    
    # With 2-day minimum, should find the event
    events = identify_discount_events(df, min_duration_days=2)
    assert len(events) > 0


def test_calculate_churn_events():
    """Test churn event calculation"""
    # Create declining player data
    data = []
    
    # Game 1: Declines and churns
    for i in range(12):
        data.append({
            "game_id": 1,
            "date": datetime(2024, 1, 1) + timedelta(days=30*i),
            "avg_players": max(100, 1000 - (i * 100)),  # Steady decline
        })
    
    # Game 2: Stable, doesn't churn
    for i in range(12):
        data.append({
            "game_id": 2,
            "date": datetime(2024, 1, 1) + timedelta(days=30*i),
            "avg_players": 1000 + np.random.normal(0, 50),  # Stable
        })
    
    df = pd.DataFrame(data)
    
    churn_events = calculate_churn_events(
        df,
        player_threshold_pct=0.5,
        lookback_months=3,
    )
    
    assert len(churn_events) > 0
    assert "game_id" in churn_events.columns
    assert "churned" in churn_events.columns
    assert "time_to_churn_months" in churn_events.columns
    
    # Game 1 should be marked as churned
    game1_churn = churn_events[churn_events["game_id"] == 1]
    assert len(game1_churn) > 0
    if len(game1_churn) > 0:
        assert game1_churn.iloc[0]["churned"] == True
    
    # Game 2 should not be churned
    game2_churn = churn_events[churn_events["game_id"] == 2]
    if len(game2_churn) > 0:
        assert game2_churn.iloc[0]["churned"] == False


def test_prepare_panel_data(sample_df):
    """Test panel data preparation"""
    panel_df = prepare_panel_data(
        sample_df,
        id_col="game_id",
        time_col="date",
    )
    
    assert "time_period" in panel_df.columns
    
    # Check lagged variables were created
    assert "avg_players_lag1" in panel_df.columns
    assert "avg_players_lag2" in panel_df.columns
    assert "current_price_lag1" in panel_df.columns
    
    # First observation should have NaN lags
    first_obs = panel_df[panel_df["time_period"] == 0].iloc[0]
    assert pd.isna(first_obs["avg_players_lag1"])


def test_validate_parallel_trends():
    """Test parallel trends validation"""
    np.random.seed(42)
    
    # Create treatment group with similar pre-trend to control
    treatment_data = []
    control_data = []
    
    for t in range(6):
        # Both groups follow similar trend pre-treatment
        base = 1000 + t * 20
        
        treatment_data.append({
            "time_period": t,
            "avg_players": base + np.random.normal(0, 30),
        })
        
        control_data.append({
            "time_period": t,
            "avg_players": base + np.random.normal(0, 30),
        })
    
    treatment_df = pd.DataFrame(treatment_data)
    control_df = pd.DataFrame(control_data)
    
    results = validate_parallel_trends(
        treatment_df,
        control_df,
        outcome_col="avg_players",
        pre_treatment_periods=5,
    )
    
    assert "treatment_slope" in results
    assert "control_slope" in results
    assert "slope_difference" in results
    assert "parallel_trends_valid" in results
    
    # Slopes should be similar
    assert abs(results["treatment_slope"] - results["control_slope"]) < 50


def test_validate_parallel_trends_violation():
    """Test parallel trends when trends are not parallel"""
    np.random.seed(42)
    
    # Create diverging pre-trends
    treatment_data = []
    control_data = []
    
    for t in range(6):
        treatment_data.append({
            "time_period": t,
            "avg_players": 1000 + t * 100,  # Steep increase
        })
        
        control_data.append({
            "time_period": t,
            "avg_players": 1000 - t * 50,  # Declining
        })
    
    treatment_df = pd.DataFrame(treatment_data)
    control_df = pd.DataFrame(control_data)
    
    results = validate_parallel_trends(
        treatment_df,
        control_df,
        outcome_col="avg_players",
        pre_treatment_periods=5,
    )
    
    # Should detect that trends are NOT parallel
    assert results["parallel_trends_valid"] == False


def test_churn_events_insufficient_data():
    """Test churn calculation with insufficient data"""
    # Very short time series
    data = pd.DataFrame({
        "game_id": [1, 1],
        "date": [datetime(2024, 1, 1), datetime(2024, 2, 1)],
        "avg_players": [1000, 900],
    })
    
    churn_events = calculate_churn_events(data, lookback_months=3)
    
    # Should handle gracefully (might return empty or minimal data)
    assert isinstance(churn_events, pd.DataFrame)


def test_discount_events_no_discounts():
    """Test discount identification when no discounts exist"""
    data = pd.DataFrame({
        "game_id": [1] * 10,
        "date": pd.date_range("2024-01-01", periods=10, freq="D"),
        "discount_pct": [0.0] * 10,
        "is_discount_active": [False] * 10,
    })
    
    events = identify_discount_events(data)
    
    # Should return empty DataFrame
    assert len(events) == 0


def test_panel_data_sorting():
    """Test that panel data is properly sorted"""
    # Create unsorted data
    data = pd.DataFrame({
        "game_id": [2, 1, 2, 1],
        "date": [
            datetime(2024, 2, 1),
            datetime(2024, 1, 1),
            datetime(2024, 1, 1),
            datetime(2024, 2, 1),
        ],
        "avg_players": [100, 200, 300, 400],
    })
    
    panel = prepare_panel_data(data)
    
    # Check that it's sorted by game_id and date
    assert panel.iloc[0]["game_id"] == 1
    assert panel.iloc[0]["date"] == datetime(2024, 1, 1)
    assert panel.iloc[-1]["game_id"] == 2
    assert panel.iloc[-1]["date"] == datetime(2024, 2, 1)
