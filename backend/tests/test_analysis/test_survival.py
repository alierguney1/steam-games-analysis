"""
Tests for Survival Analysis Module
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.analysis.survival import (
    SurvivalAnalysisModel,
    run_survival_analysis,
)


@pytest.fixture
def churn_data():
    """Create sample churn data"""
    np.random.seed(42)
    
    data = []
    
    # Genre A: Lower churn rate (better retention)
    for i in range(50):
        churned = np.random.random() < 0.3
        time_to_churn = np.random.exponential(12) if churned else np.random.uniform(12, 24)
        
        data.append({
            "game_id": i,
            "time_to_churn_months": time_to_churn,
            "churned": 1 if churned else 0,
            "genre_name": "RPG",
            "current_price": np.random.uniform(10, 30),
        })
    
    # Genre B: Higher churn rate
    for i in range(50, 100):
        churned = np.random.random() < 0.6
        time_to_churn = np.random.exponential(6) if churned else np.random.uniform(6, 12)
        
        data.append({
            "game_id": i,
            "time_to_churn_months": time_to_churn,
            "churned": 1 if churned else 0,
            "genre_name": "Indie",
            "current_price": np.random.uniform(5, 15),
        })
    
    return pd.DataFrame(data)


@pytest.fixture
def player_time_series_data():
    """Create sample player time series data for churn calculation"""
    np.random.seed(42)
    
    data = []
    start_date = datetime(2024, 1, 1)
    
    # Game 1: Gradual decline (will churn)
    for i in range(12):
        date = start_date + timedelta(days=30*i)
        avg_players = max(100, 1000 - (i * 100) + np.random.normal(0, 50))
        
        data.append({
            "game_id": 1,
            "date": date,
            "avg_players": avg_players,
            "genre_name": "Action",
        })
    
    # Game 2: Stable (won't churn)
    for i in range(12):
        date = start_date + timedelta(days=30*i)
        avg_players = 1000 + np.random.normal(0, 100)
        
        data.append({
            "game_id": 2,
            "date": date,
            "avg_players": avg_players,
            "genre_name": "RPG",
        })
    
    return pd.DataFrame(data)


def test_survival_model_initialization(churn_data):
    """Test survival model initialization"""
    model = SurvivalAnalysisModel(
        churn_data,
        duration_col="time_to_churn_months",
        event_col="churned",
    )
    
    assert model is not None
    assert len(model.data) == len(churn_data)
    assert model.duration_col == "time_to_churn_months"
    assert model.event_col == "churned"


def test_kaplan_meier_overall(churn_data):
    """Test Kaplan-Meier analysis without stratification"""
    model = SurvivalAnalysisModel(churn_data)
    
    results = model.kaplan_meier_analysis(groupby_col=None)
    
    assert "overall" in results
    assert "median_survival_time" in results["overall"]
    assert "survival_function" in results["overall"]
    assert "confidence_interval_lower" in results["overall"]
    assert "confidence_interval_upper" in results["overall"]
    
    # Median survival time should be positive
    assert results["overall"]["median_survival_time"] > 0


def test_kaplan_meier_stratified(churn_data):
    """Test Kaplan-Meier analysis with stratification by genre"""
    model = SurvivalAnalysisModel(churn_data)
    
    results = model.kaplan_meier_analysis(groupby_col="genre_name")
    
    assert "stratified" in results
    assert "groups" in results["stratified"]
    assert "logrank_test" in results
    
    # Should have survival curves for both genres
    assert "RPG" in results["stratified"]["groups"]
    assert "Indie" in results["stratified"]["groups"]
    
    # RPG should have higher median survival (lower churn) than Indie
    rpg_median = results["stratified"]["groups"]["RPG"]["median_survival_time"]
    indie_median = results["stratified"]["groups"]["Indie"]["median_survival_time"]
    
    if rpg_median and indie_median:
        assert rpg_median > indie_median


def test_cox_proportional_hazards(churn_data):
    """Test Cox PH model"""
    model = SurvivalAnalysisModel(churn_data)
    
    results = model.cox_proportional_hazards(
        covariates=["current_price"],
    )
    
    assert "coefficients" in results
    assert "hazard_ratios" in results
    assert "p_values" in results
    assert "concordance_index" in results
    assert "n_obs" in results
    assert "n_events" in results
    
    # C-index should be between 0 and 1
    assert 0 <= results["concordance_index"] <= 1
    
    # Should have coefficient for current_price
    assert "current_price" in results["coefficients"]


def test_retention_metrics(churn_data):
    """Test retention metrics calculation"""
    model = SurvivalAnalysisModel(churn_data)
    
    # First run KM to enable retention_at_time calculation
    model.kaplan_meier_analysis(groupby_col=None)
    
    metrics = model.calculate_retention_metrics()
    
    assert "n_total" in metrics
    assert "n_churned" in metrics
    assert "n_active" in metrics
    assert "churn_rate" in metrics
    assert "retention_rate" in metrics
    
    # Basic sanity checks
    assert metrics["n_total"] == len(churn_data)
    assert metrics["n_churned"] + metrics["n_active"] == metrics["n_total"]
    assert 0 <= metrics["churn_rate"] <= 1
    assert 0 <= metrics["retention_rate"] <= 1
    assert abs(metrics["churn_rate"] + metrics["retention_rate"] - 1.0) < 0.01


def test_predict_survival(churn_data):
    """Test survival probability prediction"""
    model = SurvivalAnalysisModel(churn_data)
    
    # Fit Cox PH model first
    model.cox_proportional_hazards(covariates=["current_price"])
    
    # Predict for a specific covariate value
    predictions = model.predict_survival(
        covariate_values={"current_price": 20.0},
        times=[3, 6, 12, 24],
    )
    
    assert "survival_probabilities" in predictions
    assert "times" in predictions
    assert len(predictions["survival_probabilities"]) > 0


def test_run_survival_analysis(player_time_series_data):
    """Test complete survival analysis pipeline"""
    results = run_survival_analysis(
        player_time_series_data,
        churn_threshold_pct=0.5,
        groupby_col="genre_name",
        covariates=None,
    )
    
    assert "kaplan_meier" in results
    assert "retention_metrics" in results
    assert "diagnostics" in results
    
    # Check diagnostics
    assert results["diagnostics"]["n_games_analyzed"] > 0
    assert results["diagnostics"]["churn_threshold_pct"] == 0.5


def test_survival_with_insufficient_data():
    """Test survival analysis handles insufficient data gracefully"""
    # Very small dataset
    small_data = pd.DataFrame({
        "game_id": [1, 2],
        "time_to_churn_months": [5, 10],
        "churned": [1, 0],
    })
    
    model = SurvivalAnalysisModel(small_data)
    
    # Should still work but with limited results
    results = model.kaplan_meier_analysis()
    assert "overall" in results


def test_survival_all_censored():
    """Test survival when all observations are censored"""
    all_censored = pd.DataFrame({
        "game_id": range(10),
        "time_to_churn_months": np.random.uniform(5, 15, 10),
        "churned": [0] * 10,  # All censored
    })
    
    model = SurvivalAnalysisModel(all_censored)
    results = model.kaplan_meier_analysis()
    
    assert "overall" in results
    # Median might be undefined if no events occurred
