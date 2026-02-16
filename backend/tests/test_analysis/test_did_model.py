"""
Tests for DiD (Difference-in-Differences) Model
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.analysis.did_model import (
    DifferenceInDifferencesModel,
    run_did_analysis,
)


@pytest.fixture
def sample_data():
    """Create sample treatment and control data"""
    np.random.seed(42)
    
    # Generate dates
    start_date = datetime(2024, 1, 1)
    dates = [start_date + timedelta(days=30*i) for i in range(12)]
    
    # Treatment group (discount applied at month 6)
    treatment_data = []
    for i, date in enumerate(dates):
        # Pre-treatment: avg ~1000 players
        # Post-treatment: avg ~1200 players (20% increase)
        base_players = 1000 + np.random.normal(0, 100)
        treatment_effect = 200 if i >= 6 else 0
        avg_players = base_players + treatment_effect + np.random.normal(0, 50)
        
        treatment_data.append({
            "game_id": 1,
            "date": date,
            "avg_players": max(0, avg_players),
            "current_price": 19.99,
            "discount_pct": 30.0 if i >= 6 else 0.0,
            "is_discount_active": i >= 6,
            "genre_name": "Action",
        })
    
    # Control group (no discount)
    control_data = []
    for i, date in enumerate(dates):
        # Similar baseline but no treatment effect
        avg_players = 1000 + np.random.normal(0, 100) + np.random.normal(0, 50)
        
        control_data.append({
            "game_id": 2,
            "date": date,
            "avg_players": max(0, avg_players),
            "current_price": 19.99,
            "discount_pct": 0.0,
            "is_discount_active": False,
            "genre_name": "Action",
        })
    
    treatment_df = pd.DataFrame(treatment_data)
    control_df = pd.DataFrame(control_data)
    
    return treatment_df, control_df


def test_did_initialization(sample_data):
    """Test DiD model initialization"""
    treatment_df, control_df = sample_data
    
    model = DifferenceInDifferencesModel(
        treatment_df,
        control_df,
        outcome_col="avg_players",
    )
    
    assert model is not None
    assert model.outcome_col == "avg_players"
    assert len(model.treatment_df) == len(treatment_df)
    assert len(model.control_df) == len(control_df)


def test_did_estimation(sample_data):
    """Test DiD estimation with known treatment effect"""
    treatment_df, control_df = sample_data
    
    # Set explicit treatment date
    treatment_date = datetime(2024, 7, 1)
    
    model = DifferenceInDifferencesModel(
        treatment_df,
        control_df,
        outcome_col="avg_players",
        treatment_date=treatment_date,
    )
    
    results = model.estimate(include_covariates=False)
    
    # Check that results contain expected keys
    assert "att" in results
    assert "p_value" in results
    assert "standard_error" in results
    assert "r_squared" in results
    assert "conf_int_lower" in results
    assert "conf_int_upper" in results
    
    # ATT should be positive (around 200) given our data generation
    assert results["att"] > 0
    
    # Should have reasonable number of observations
    assert results["n_obs"] > 0


def test_did_parallel_trends(sample_data):
    """Test parallel trends validation"""
    treatment_df, control_df = sample_data
    
    model = DifferenceInDifferencesModel(
        treatment_df,
        control_df,
        outcome_col="avg_players",
    )
    
    trends = model.parallel_trends_test()
    
    assert "treatment_slope" in trends
    assert "control_slope" in trends
    assert "slope_difference" in trends
    assert "parallel_trends_valid" in trends


def test_did_placebo_test(sample_data):
    """Test placebo test with fake treatment date"""
    treatment_df, control_df = sample_data
    
    treatment_date = datetime(2024, 7, 1)
    fake_date = datetime(2024, 3, 1)  # Before actual treatment
    
    model = DifferenceInDifferencesModel(
        treatment_df,
        control_df,
        outcome_col="avg_players",
        treatment_date=treatment_date,
    )
    
    placebo = model.placebo_test(fake_date)
    
    assert "placebo_att" in placebo
    assert "placebo_p_value" in placebo
    assert "placebo_significant" in placebo
    
    # Placebo should ideally NOT be significant
    # (though with small sample it might be by chance)


def test_did_event_study(sample_data):
    """Test event study analysis"""
    treatment_df, control_df = sample_data
    
    treatment_date = datetime(2024, 7, 1)
    
    model = DifferenceInDifferencesModel(
        treatment_df,
        control_df,
        outcome_col="avg_players",
        treatment_date=treatment_date,
    )
    
    event_df = model.event_study(periods_before=3, periods_after=3)
    
    assert len(event_df) > 0
    assert "event_time" in event_df.columns
    assert "coefficient" in event_df.columns
    assert "p_value" in event_df.columns


def test_run_did_analysis(sample_data):
    """Test complete DiD analysis pipeline"""
    treatment_df, control_df = sample_data
    
    results = run_did_analysis(
        treatment_df,
        control_df,
        outcome_col="avg_players",
        run_placebo=True,
        run_event_study=True,
    )
    
    assert "main_estimation" in results
    assert "parallel_trends" in results
    assert "placebo_test" in results
    assert "event_study" in results
    assert "diagnostics" in results
    
    # Check diagnostics
    assert results["diagnostics"]["treatment_group_size"] == len(treatment_df)
    assert results["diagnostics"]["control_group_size"] == len(control_df)


def test_did_with_missing_data():
    """Test DiD handles missing data appropriately"""
    # Create data with some missing values
    treatment_df = pd.DataFrame({
        "game_id": [1] * 5,
        "date": pd.date_range("2024-01-01", periods=5, freq="ME"),
        "avg_players": [1000, np.nan, 1200, 1150, 1300],
        "current_price": [19.99] * 5,
        "is_discount_active": [False, False, True, True, True],
        "discount_pct": [0.0, 0.0, 30.0, 30.0, 30.0],
    })
    
    control_df = pd.DataFrame({
        "game_id": [2] * 5,
        "date": pd.date_range("2024-01-01", periods=5, freq="ME"),
        "avg_players": [1000, 980, 1020, np.nan, 1010],
        "current_price": [19.99] * 5,
        "is_discount_active": [False, False, False, False, False],
        "discount_pct": [0.0, 0.0, 0.0, 0.0, 0.0],
    })
    
    model = DifferenceInDifferencesModel(
        treatment_df,
        control_df,
        outcome_col="avg_players",
    )
    
    # Should not raise error, should handle missing values
    results = model.estimate(include_covariates=False)
    assert results["n_obs"] < 10  # Some observations dropped
