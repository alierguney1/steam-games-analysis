"""
Difference-in-Differences (DiD) Analysis Module
Causal inference for measuring treatment effects (e.g., price discounts on player counts)
"""

from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
from statsmodels.api import OLS, add_constant
from statsmodels.stats.diagnostic import het_breuschpagan
import logging

from app.analysis.utils import (
    prepare_panel_data,
    validate_parallel_trends,
    identify_discount_events,
)

logger = logging.getLogger(__name__)


class DifferenceInDifferencesModel:
    """
    Difference-in-Differences Estimator
    
    Measures the causal effect of a treatment (e.g., discount event) on an outcome
    (e.g., player count) by comparing treatment and control groups before and after.
    
    Model: Y_it = β0 + β1*Treatment_i + β2*Post_t + β3*(Treatment_i × Post_t) + ε_it
    
    Where β3 is the Average Treatment Effect on Treated (ATT)
    """
    
    def __init__(
        self,
        treatment_df: pd.DataFrame,
        control_df: pd.DataFrame,
        outcome_col: str = "avg_players",
        treatment_date: Optional[datetime] = None,
    ):
        """
        Initialize DiD model
        
        Args:
            treatment_df: DataFrame for treatment group
            control_df: DataFrame for control group
            outcome_col: Column name for outcome variable
            treatment_date: Date when treatment occurred (auto-detected if None)
        """
        self.treatment_df = prepare_panel_data(treatment_df)
        self.control_df = prepare_panel_data(control_df)
        self.outcome_col = outcome_col
        self.treatment_date = treatment_date
        
        self.model_result = None
        self.att = None
        self.standard_error = None
        self.p_value = None
        
    def _prepare_did_data(self) -> pd.DataFrame:
        """
        Prepare combined dataset for DiD regression
        
        Returns:
            DataFrame with treatment, post, and interaction terms
        """
        # Mark treatment group
        self.treatment_df["treatment"] = 1
        self.control_df["treatment"] = 0
        
        # Combine datasets
        combined = pd.concat([self.treatment_df, self.control_df], ignore_index=True)
        
        # Determine treatment date if not provided
        if self.treatment_date is None:
            # Use median date of discount events in treatment group
            discount_events = identify_discount_events(self.treatment_df)
            if len(discount_events) > 0:
                self.treatment_date = discount_events["start_date"].median()
            else:
                # Fallback: use midpoint of data
                self.treatment_date = combined["date"].median()
        
        # Create post-treatment indicator
        combined["post"] = (combined["date"] >= self.treatment_date).astype(int)
        
        # Create interaction term (DiD estimator)
        combined["treatment_post"] = combined["treatment"] * combined["post"]
        
        return combined
    
    def estimate(self, include_covariates: bool = True) -> Dict:
        """
        Estimate DiD model using OLS regression
        
        Args:
            include_covariates: Whether to include additional control variables
        
        Returns:
            Dictionary with estimation results
        """
        did_data = self._prepare_did_data()
        
        # Remove missing values
        did_data = did_data.dropna(subset=[self.outcome_col])
        
        if len(did_data) == 0:
            raise ValueError("No valid data for DiD estimation")
        
        # Prepare regression variables
        X_cols = ["treatment", "post", "treatment_post"]
        
        if include_covariates:
            # Add covariates if available
            if "current_price" in did_data.columns:
                X_cols.append("current_price")
            if "genre_name" in did_data.columns:
                # Add genre dummies (if multiple genres exist)
                genre_dummies = pd.get_dummies(did_data["genre_name"], prefix="genre", drop_first=True)
                did_data = pd.concat([did_data, genre_dummies], axis=1)
                X_cols.extend(genre_dummies.columns.tolist())
        
        # Prepare X and y
        X = did_data[X_cols].fillna(0)
        X = add_constant(X)
        y = did_data[self.outcome_col]
        
        # Run OLS regression
        try:
            model = OLS(y, X)
            self.model_result = model.fit()
            
            # Extract ATT (coefficient on treatment_post interaction)
            self.att = self.model_result.params["treatment_post"]
            self.standard_error = self.model_result.bse["treatment_post"]
            self.p_value = self.model_result.pvalues["treatment_post"]
            
            # Calculate confidence intervals
            conf_int = self.model_result.conf_int(alpha=0.05)
            att_ci_lower = conf_int.loc["treatment_post", 0]
            att_ci_upper = conf_int.loc["treatment_post", 1]
            
            # Heteroskedasticity test
            _, het_pvalue, _, _ = het_breuschpagan(
                self.model_result.resid, self.model_result.model.exog
            )
            
            results = {
                "att": float(self.att),
                "standard_error": float(self.standard_error),
                "p_value": float(self.p_value),
                "conf_int_lower": float(att_ci_lower),
                "conf_int_upper": float(att_ci_upper),
                "r_squared": float(self.model_result.rsquared),
                "adj_r_squared": float(self.model_result.rsquared_adj),
                "n_obs": int(self.model_result.nobs),
                "treatment_date": self.treatment_date.isoformat() if self.treatment_date else None,
                "heteroskedasticity_pvalue": float(het_pvalue),
                "model_params": {
                    k: float(v) for k, v in self.model_result.params.items()
                },
            }
            
            logger.info(f"DiD estimation complete: ATT={self.att:.2f}, p={self.p_value:.4f}")
            
            return results
            
        except Exception as e:
            logger.error(f"DiD estimation failed: {str(e)}")
            raise
    
    def parallel_trends_test(self) -> Dict:
        """
        Test parallel trends assumption
        
        Returns:
            Dictionary with test results
        """
        results = validate_parallel_trends(
            self.treatment_df,
            self.control_df,
            outcome_col=self.outcome_col,
            pre_treatment_periods=3,
        )
        
        logger.info(
            f"Parallel trends test: slope_diff={results['slope_difference']:.4f}, "
            f"valid={results['parallel_trends_valid']}"
        )
        
        return results
    
    def placebo_test(self, fake_treatment_date: datetime) -> Dict:
        """
        Placebo test using a fake treatment date
        
        This tests whether the model incorrectly finds an effect at a time
        when no treatment occurred.
        
        Args:
            fake_treatment_date: Date to use as fake treatment
        
        Returns:
            Dictionary with placebo test results
        """
        # Create a copy with fake treatment date
        placebo_model = DifferenceInDifferencesModel(
            self.treatment_df.copy(),
            self.control_df.copy(),
            outcome_col=self.outcome_col,
            treatment_date=fake_treatment_date,
        )
        
        # Run estimation
        placebo_results = placebo_model.estimate(include_covariates=False)
        
        logger.info(
            f"Placebo test: ATT={placebo_results['att']:.2f}, "
            f"p={placebo_results['p_value']:.4f}"
        )
        
        return {
            "placebo_att": placebo_results["att"],
            "placebo_p_value": placebo_results["p_value"],
            "placebo_significant": placebo_results["p_value"] < 0.05,
            "placebo_date": fake_treatment_date.isoformat(),
        }
    
    def event_study(self, periods_before: int = 3, periods_after: int = 3) -> pd.DataFrame:
        """
        Event study analysis to visualize treatment effects over time
        
        Args:
            periods_before: Number of periods before treatment to include
            periods_after: Number of periods after treatment to include
        
        Returns:
            DataFrame with event time coefficients
        """
        did_data = self._prepare_did_data()
        
        # Create event time variable (periods relative to treatment)
        did_data["event_time"] = did_data.apply(
            lambda row: (
                (row["date"].year - self.treatment_date.year) * 12 
                + (row["date"].month - self.treatment_date.month)
            ),
            axis=1,
        )
        
        # Filter to event window
        event_data = did_data[
            (did_data["event_time"] >= -periods_before) &
            (did_data["event_time"] <= periods_after)
        ]
        
        # Create event time dummies
        event_dummies = pd.get_dummies(
            event_data["event_time"], 
            prefix="event_t",
            drop_first=True,  # Drop t=-periods_before as reference
        )
        
        # Interact with treatment
        for col in event_dummies.columns:
            event_data[f"treatment_{col}"] = (
                event_data["treatment"] * event_dummies[col]
            )
        
        # Prepare regression
        X_cols = ["treatment"] + [f"treatment_{col}" for col in event_dummies.columns]
        X = event_data[X_cols].fillna(0)
        X = add_constant(X)
        y = event_data[self.outcome_col]
        
        # Run regression
        model = OLS(y, X)
        result = model.fit()
        
        # Extract coefficients for event time
        event_coeffs = []
        for col in event_dummies.columns:
            treatment_col = f"treatment_{col}"
            if treatment_col in result.params:
                event_time = int(col.split("_")[-1])
                event_coeffs.append({
                    "event_time": event_time,
                    "coefficient": result.params[treatment_col],
                    "std_error": result.bse[treatment_col],
                    "p_value": result.pvalues[treatment_col],
                })
        
        event_df = pd.DataFrame(event_coeffs)
        
        logger.info(f"Event study complete: {len(event_df)} time periods analyzed")
        
        return event_df


def run_did_analysis(
    treatment_df: pd.DataFrame,
    control_df: pd.DataFrame,
    outcome_col: str = "avg_players",
    treatment_date: Optional[datetime] = None,
    run_placebo: bool = True,
    run_event_study: bool = True,
) -> Dict:
    """
    Run complete DiD analysis with diagnostic tests
    
    Args:
        treatment_df: Treatment group data
        control_df: Control group data
        outcome_col: Outcome variable name
        treatment_date: Treatment date (auto-detected if None)
        run_placebo: Whether to run placebo test
        run_event_study: Whether to run event study
    
    Returns:
        Dictionary with complete analysis results
    """
    # Initialize model
    did_model = DifferenceInDifferencesModel(
        treatment_df, control_df, outcome_col, treatment_date
    )
    
    # Main estimation
    main_results = did_model.estimate(include_covariates=True)
    
    # Parallel trends test
    parallel_trends = did_model.parallel_trends_test()
    
    # Placebo test (use date 3 months before actual treatment)
    placebo_results = None
    if run_placebo and did_model.treatment_date:
        fake_date = did_model.treatment_date - pd.DateOffset(months=3)
        try:
            placebo_results = did_model.placebo_test(fake_date)
        except Exception as e:
            logger.warning(f"Placebo test failed: {str(e)}")
    
    # Event study
    event_study_results = None
    if run_event_study:
        try:
            event_study_df = did_model.event_study(periods_before=3, periods_after=3)
            event_study_results = event_study_df.to_dict(orient="records")
        except Exception as e:
            logger.warning(f"Event study failed: {str(e)}")
    
    # Compile results
    results = {
        "main_estimation": main_results,
        "parallel_trends": parallel_trends,
        "placebo_test": placebo_results,
        "event_study": event_study_results,
        "diagnostics": {
            "treatment_group_size": len(treatment_df),
            "control_group_size": len(control_df),
            "outcome_variable": outcome_col,
        },
    }
    
    return results
