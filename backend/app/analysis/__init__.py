"""
Analysis Module
Statistical and econometric models for causal inference, survival analysis, and price elasticity
"""

from app.analysis.did_model import (
    DifferenceInDifferencesModel,
    run_did_analysis,
)
from app.analysis.survival import (
    SurvivalAnalysisModel,
    run_survival_analysis,
)
from app.analysis.elasticity import (
    PriceElasticityModel,
    run_elasticity_analysis,
    calculate_elasticity_heatmap,
)
from app.analysis.utils import (
    fetch_player_price_data,
    create_cohorts,
    identify_discount_events,
    calculate_churn_events,
    prepare_panel_data,
    validate_parallel_trends,
)

__all__ = [
    # DiD
    "DifferenceInDifferencesModel",
    "run_did_analysis",
    # Survival
    "SurvivalAnalysisModel",
    "run_survival_analysis",
    # Elasticity
    "PriceElasticityModel",
    "run_elasticity_analysis",
    "calculate_elasticity_heatmap",
    # Utils
    "fetch_player_price_data",
    "create_cohorts",
    "identify_discount_events",
    "calculate_churn_events",
    "prepare_panel_data",
    "validate_parallel_trends",
]
