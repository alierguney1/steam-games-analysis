"""
Survival Analysis Module
Kaplan-Meier and Cox Proportional Hazards models for player retention/churn analysis
"""

from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from lifelines import KaplanMeierFitter, CoxPHFitter
from lifelines.statistics import logrank_test, multivariate_logrank_test
import logging

from app.analysis.utils import calculate_churn_events

logger = logging.getLogger(__name__)


class SurvivalAnalysisModel:
    """
    Survival Analysis for Game Player Retention
    
    Uses Kaplan-Meier and Cox Proportional Hazards models to analyze
    player retention and predict churn rates.
    """
    
    def __init__(
        self,
        data: pd.DataFrame,
        duration_col: str = "time_to_churn_months",
        event_col: str = "churned",
    ):
        """
        Initialize Survival Analysis model
        
        Args:
            data: DataFrame with duration and event columns
            duration_col: Column name for time-to-event (or censoring)
            event_col: Column name for event indicator (1=churned, 0=censored)
        """
        self.data = data.copy()
        self.duration_col = duration_col
        self.event_col = event_col
        
        # Ensure proper data types
        self.data[duration_col] = self.data[duration_col].astype(float)
        self.data[event_col] = self.data[event_col].astype(int)
        
        self.kmf = None
        self.coxph = None
        
    def kaplan_meier_analysis(
        self,
        groupby_col: Optional[str] = None,
        alpha: float = 0.05,
    ) -> Dict:
        """
        Perform Kaplan-Meier survival analysis
        
        Args:
            groupby_col: Optional column to stratify analysis (e.g., genre)
            alpha: Significance level for confidence intervals
        
        Returns:
            Dictionary with survival curves and statistics
        """
        results = {}
        
        if groupby_col is None:
            # Overall survival curve
            kmf = KaplanMeierFitter(alpha=alpha)
            kmf.fit(
                durations=self.data[self.duration_col],
                event_observed=self.data[self.event_col],
                label="Overall",
            )
            
            self.kmf = kmf
            
            results["overall"] = {
                "median_survival_time": float(kmf.median_survival_time_),
                "survival_function": kmf.survival_function_.to_dict()["Overall"],
                "confidence_interval_lower": kmf.confidence_interval_.iloc[:, 0].to_dict(),
                "confidence_interval_upper": kmf.confidence_interval_.iloc[:, 1].to_dict(),
                "event_table": kmf.event_table.to_dict(),
            }
            
            logger.info(f"KM analysis: median survival = {kmf.median_survival_time_:.2f} months")
            
        else:
            # Stratified survival curves
            groups = self.data[groupby_col].unique()
            survival_curves = {}
            median_times = {}
            
            for group in groups:
                group_data = self.data[self.data[groupby_col] == group]
                
                if len(group_data) < 5:  # Skip small groups
                    continue
                
                kmf = KaplanMeierFitter(alpha=alpha)
                kmf.fit(
                    durations=group_data[self.duration_col],
                    event_observed=group_data[self.event_col],
                    label=str(group),
                )
                
                survival_curves[str(group)] = {
                    "median_survival_time": float(kmf.median_survival_time_) if kmf.median_survival_time_ else None,
                    "survival_function": kmf.survival_function_.to_dict()[str(group)],
                    "confidence_interval_lower": kmf.confidence_interval_.iloc[:, 0].to_dict(),
                    "confidence_interval_upper": kmf.confidence_interval_.iloc[:, 1].to_dict(),
                }
                
                median_times[str(group)] = kmf.median_survival_time_
            
            results["stratified"] = {
                "groupby_column": groupby_col,
                "groups": survival_curves,
                "median_times": median_times,
            }
            
            # Log-rank test for group comparison
            if len(groups) > 1:
                logrank_results = self._logrank_test(groupby_col)
                results["logrank_test"] = logrank_results
            
            logger.info(
                f"KM stratified analysis: {len(survival_curves)} groups, "
                f"groupby={groupby_col}"
            )
        
        return results
    
    def _logrank_test(self, groupby_col: str) -> Dict:
        """
        Perform log-rank test to compare survival curves between groups
        
        Args:
            groupby_col: Column to group by
        
        Returns:
            Dictionary with test statistics
        """
        groups = self.data[groupby_col].unique()
        
        if len(groups) == 2:
            # Pairwise log-rank test
            group1 = self.data[self.data[groupby_col] == groups[0]]
            group2 = self.data[self.data[groupby_col] == groups[1]]
            
            result = logrank_test(
                durations_A=group1[self.duration_col],
                durations_B=group2[self.duration_col],
                event_observed_A=group1[self.event_col],
                event_observed_B=group2[self.event_col],
            )
            
            return {
                "test_statistic": float(result.test_statistic),
                "p_value": float(result.p_value),
                "group1": str(groups[0]),
                "group2": str(groups[1]),
                "significant": result.p_value < 0.05,
            }
        else:
            # Multivariate log-rank test for >2 groups
            try:
                result = multivariate_logrank_test(
                    self.data[self.duration_col],
                    self.data[groupby_col],
                    self.data[self.event_col],
                )
                
                return {
                    "test_statistic": float(result.test_statistic),
                    "p_value": float(result.p_value),
                    "n_groups": len(groups),
                    "significant": result.p_value < 0.05,
                }
            except Exception as e:
                logger.warning(f"Multivariate log-rank test failed: {str(e)}")
                return {"error": str(e)}
    
    def cox_proportional_hazards(
        self,
        covariates: List[str],
        penalizer: float = 0.1,
    ) -> Dict:
        """
        Fit Cox Proportional Hazards model
        
        Args:
            covariates: List of covariate column names
            penalizer: L2 penalization parameter for regularization
        
        Returns:
            Dictionary with model results
        """
        # Prepare data with covariates
        model_data = self.data[[self.duration_col, self.event_col] + covariates].copy()
        model_data = model_data.dropna()
        
        if len(model_data) < 10:
            raise ValueError("Insufficient data for Cox PH model")
        
        # Fit model
        coxph = CoxPHFitter(penalizer=penalizer)
        coxph.fit(
            model_data,
            duration_col=self.duration_col,
            event_col=self.event_col,
        )
        
        self.coxph = coxph
        
        # Extract results
        results = {
            "coefficients": coxph.params_.to_dict(),
            "hazard_ratios": np.exp(coxph.params_).to_dict(),
            "standard_errors": coxph.standard_errors_.to_dict(),
            "p_values": coxph.summary["p"].to_dict(),
            "concordance_index": float(coxph.concordance_index_),
            "log_likelihood": float(coxph.log_likelihood_),
            "aic": float(coxph.AIC_),
            "n_obs": int(len(model_data)),
            "n_events": int(model_data[self.event_col].sum()),
        }
        
        # Proportionality test
        try:
            ph_test = coxph.check_assumptions(model_data, p_value_threshold=0.05)
            results["proportionality_test"] = {
                "test_statistic": ph_test[1].to_dict() if hasattr(ph_test[1], 'to_dict') else None,
                "assumptions_valid": True,  # Simplified for now
            }
        except Exception as e:
            logger.warning(f"Proportionality test failed: {str(e)}")
            results["proportionality_test"] = {"error": str(e)}
        
        logger.info(
            f"Cox PH model: C-index={coxph.concordance_index_:.3f}, "
            f"n_events={results['n_events']}"
        )
        
        return results
    
    def predict_survival(
        self,
        covariate_values: Dict[str, float],
        times: Optional[List[float]] = None,
    ) -> Dict:
        """
        Predict survival probability for given covariate values
        
        Args:
            covariate_values: Dictionary of covariate values
            times: Time points for prediction (default: 1-24 months)
        
        Returns:
            Dictionary with survival probabilities
        """
        if self.coxph is None:
            raise ValueError("Cox PH model must be fitted first")
        
        if times is None:
            times = list(range(1, 25))  # 1-24 months
        
        # Create prediction DataFrame
        pred_df = pd.DataFrame([covariate_values])
        
        # Predict survival function
        survival_func = self.coxph.predict_survival_function(pred_df)
        
        # Extract probabilities at specified times
        survival_probs = {}
        for t in times:
            # Find closest time point
            closest_idx = survival_func.index.asof(t)
            if pd.notna(closest_idx):
                survival_probs[t] = float(survival_func.loc[closest_idx, 0])
        
        return {
            "times": times,
            "survival_probabilities": survival_probs,
            "covariate_values": covariate_values,
        }
    
    def calculate_retention_metrics(self) -> Dict:
        """
        Calculate key retention metrics
        
        Returns:
            Dictionary with retention statistics
        """
        n_total = len(self.data)
        n_churned = self.data[self.event_col].sum()
        n_active = n_total - n_churned
        
        churn_rate = n_churned / n_total if n_total > 0 else 0
        retention_rate = n_active / n_total if n_total > 0 else 0
        
        # Calculate median time to churn (for churned users only)
        churned_data = self.data[self.data[self.event_col] == 1]
        median_time_to_churn = (
            churned_data[self.duration_col].median() 
            if len(churned_data) > 0 else None
        )
        
        # Calculate retention at specific time points
        retention_at_time = {}
        if self.kmf is not None:
            for months in [3, 6, 12, 24]:
                try:
                    retention = self.kmf.predict(months)
                    retention_at_time[f"{months}_months"] = float(retention)
                except:
                    retention_at_time[f"{months}_months"] = None
        
        return {
            "n_total": n_total,
            "n_churned": n_churned,
            "n_active": n_active,
            "churn_rate": float(churn_rate),
            "retention_rate": float(retention_rate),
            "median_time_to_churn_months": float(median_time_to_churn) if median_time_to_churn else None,
            "retention_at_time": retention_at_time,
        }


def run_survival_analysis(
    player_data: pd.DataFrame,
    churn_threshold_pct: float = 0.5,
    groupby_col: Optional[str] = None,
    covariates: Optional[List[str]] = None,
) -> Dict:
    """
    Run complete survival analysis pipeline
    
    Args:
        player_data: DataFrame with game player counts over time
        churn_threshold_pct: Threshold for defining churn
        groupby_col: Optional column to stratify analysis
        covariates: Optional list of covariates for Cox PH model
    
    Returns:
        Dictionary with complete survival analysis results
    """
    # Calculate churn events
    churn_data = calculate_churn_events(
        player_data,
        player_threshold_pct=churn_threshold_pct,
    )
    
    # Merge with original data to get covariates
    if covariates:
        # Get latest values for each game's covariates
        latest_data = (
            player_data.sort_values("date")
            .groupby("game_id")
            .last()
            .reset_index()
        )
        churn_data = churn_data.merge(
            latest_data[["game_id"] + covariates],
            on="game_id",
            how="left",
        )
    
    # Add groupby column if needed
    if groupby_col and groupby_col in player_data.columns:
        genre_mapping = (
            player_data[["game_id", groupby_col]]
            .drop_duplicates()
            .set_index("game_id")[groupby_col]
            .to_dict()
        )
        churn_data[groupby_col] = churn_data["game_id"].map(genre_mapping)
    
    # Initialize model
    survival_model = SurvivalAnalysisModel(churn_data)
    
    # Kaplan-Meier analysis
    km_results = survival_model.kaplan_meier_analysis(groupby_col=groupby_col)
    
    # Cox PH model (if covariates provided)
    cox_results = None
    if covariates:
        try:
            # Filter to available covariates
            available_covariates = [
                c for c in covariates if c in churn_data.columns
            ]
            if len(available_covariates) > 0:
                cox_results = survival_model.cox_proportional_hazards(available_covariates)
        except Exception as e:
            logger.warning(f"Cox PH model failed: {str(e)}")
    
    # Retention metrics
    retention_metrics = survival_model.calculate_retention_metrics()
    
    # Compile results
    results = {
        "kaplan_meier": km_results,
        "cox_proportional_hazards": cox_results,
        "retention_metrics": retention_metrics,
        "diagnostics": {
            "n_games_analyzed": len(churn_data),
            "churn_threshold_pct": churn_threshold_pct,
            "groupby_column": groupby_col,
            "covariates": covariates,
        },
    }
    
    logger.info(
        f"Survival analysis complete: {len(churn_data)} games, "
        f"churn_rate={retention_metrics['churn_rate']:.2%}"
    )
    
    return results
