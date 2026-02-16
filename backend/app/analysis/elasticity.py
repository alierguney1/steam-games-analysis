"""
Price Elasticity Analysis Module
Calculate demand elasticity and optimal pricing for games
"""

from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from statsmodels.api import OLS, add_constant
from scipy.optimize import minimize_scalar
import logging

logger = logging.getLogger(__name__)


class PriceElasticityModel:
    """
    Price Elasticity of Demand Calculator
    
    Measures how player demand (player counts) responds to price changes.
    Elasticity = % change in quantity / % change in price
    """
    
    def __init__(
        self,
        data: pd.DataFrame,
        price_col: str = "current_price",
        quantity_col: str = "avg_players",
    ):
        """
        Initialize Price Elasticity model
        
        Args:
            data: DataFrame with price and quantity data
            price_col: Column name for price
            quantity_col: Column name for quantity (player count)
        """
        self.data = data.copy()
        self.price_col = price_col
        self.quantity_col = quantity_col
        
        # Clean data
        self.data = self.data[
            (self.data[price_col] > 0) & (self.data[quantity_col] > 0)
        ].copy()
        
        self.elasticity = None
        self.model_result = None
    
    def calculate_arc_elasticity(
        self,
        group_by: Optional[str] = None,
    ) -> Dict:
        """
        Calculate arc (midpoint) elasticity
        
        Arc elasticity = (ΔQ/Q_avg) / (ΔP/P_avg)
        
        Args:
            group_by: Optional column to calculate elasticity by group
        
        Returns:
            Dictionary with elasticity values
        """
        results = {}
        
        if group_by is None:
            # Overall elasticity
            elasticity = self._calculate_arc_elasticity_single(self.data)
            results["overall"] = elasticity
        else:
            # Group-wise elasticity
            groups = self.data[group_by].unique()
            elasticities = {}
            
            for group in groups:
                group_data = self.data[self.data[group_by] == group]
                
                if len(group_data) < 5:  # Skip small groups
                    continue
                
                elasticity = self._calculate_arc_elasticity_single(group_data)
                elasticities[str(group)] = elasticity
            
            results["by_group"] = {
                "groupby_column": group_by,
                "elasticities": elasticities,
            }
        
        return results
    
    def _calculate_arc_elasticity_single(self, data: pd.DataFrame) -> Dict:
        """
        Calculate arc elasticity for a single group
        
        Args:
            data: DataFrame with price and quantity data
        
        Returns:
            Dictionary with elasticity value and statistics
        """
        if len(data) < 2:
            return {"elasticity": None, "error": "Insufficient data"}
        
        # Sort by price
        data = data.sort_values(self.price_col)
        
        # Calculate changes
        price_changes = []
        quantity_changes = []
        elasticities = []
        
        for i in range(1, len(data)):
            p1 = data.iloc[i-1][self.price_col]
            p2 = data.iloc[i][self.price_col]
            q1 = data.iloc[i-1][self.quantity_col]
            q2 = data.iloc[i][self.quantity_col]
            
            # Arc elasticity formula
            p_avg = (p1 + p2) / 2
            q_avg = (q1 + q2) / 2
            
            delta_p = p2 - p1
            delta_q = q2 - q1
            
            if p_avg > 0 and q_avg > 0 and delta_p != 0:
                elasticity = (delta_q / q_avg) / (delta_p / p_avg)
                elasticities.append(elasticity)
                price_changes.append(delta_p)
                quantity_changes.append(delta_q)
        
        if len(elasticities) == 0:
            return {"elasticity": None, "error": "No valid price changes"}
        
        # Average elasticity
        avg_elasticity = np.mean(elasticities)
        median_elasticity = np.median(elasticities)
        std_elasticity = np.std(elasticities)
        
        return {
            "elasticity": float(avg_elasticity),
            "median_elasticity": float(median_elasticity),
            "std_elasticity": float(std_elasticity),
            "n_observations": len(elasticities),
            "elastic": abs(avg_elasticity) > 1.0,  # Elastic if |E| > 1
            "interpretation": self._interpret_elasticity(avg_elasticity),
        }
    
    def calculate_log_log_elasticity(
        self,
        include_controls: bool = True,
        group_by: Optional[str] = None,
    ) -> Dict:
        """
        Calculate elasticity using log-log regression
        
        ln(Q) = β0 + β1*ln(P) + controls + ε
        
        Where β1 is the price elasticity of demand.
        
        Args:
            include_controls: Whether to include control variables
            group_by: Optional column to calculate by group
        
        Returns:
            Dictionary with elasticity estimates
        """
        results = {}
        
        if group_by is None:
            # Overall elasticity
            elasticity = self._estimate_log_log_single(self.data, include_controls)
            results["overall"] = elasticity
            self.elasticity = elasticity["elasticity"]
        else:
            # Group-wise elasticity
            groups = self.data[group_by].unique()
            elasticities = {}
            
            for group in groups:
                group_data = self.data[self.data[group_by] == group]
                
                if len(group_data) < 10:  # Need more data for regression
                    continue
                
                elasticity = self._estimate_log_log_single(group_data, include_controls)
                elasticities[str(group)] = elasticity
            
            results["by_group"] = {
                "groupby_column": group_by,
                "elasticities": elasticities,
            }
        
        return results
    
    def _estimate_log_log_single(
        self,
        data: pd.DataFrame,
        include_controls: bool,
    ) -> Dict:
        """
        Estimate log-log regression for a single group
        
        Args:
            data: DataFrame with price and quantity data
            include_controls: Whether to include controls
        
        Returns:
            Dictionary with elasticity estimate
        """
        # Create log-transformed variables
        data = data.copy()
        data["log_price"] = np.log(data[self.price_col])
        data["log_quantity"] = np.log(data[self.quantity_col])
        
        # Remove infinite values
        data = data.replace([np.inf, -np.inf], np.nan).dropna(
            subset=["log_price", "log_quantity"]
        )
        
        if len(data) < 10:
            return {"elasticity": None, "error": "Insufficient data"}
        
        # Prepare regression variables
        X_cols = ["log_price"]
        
        if include_controls:
            # Add discount indicator if available
            if "is_discount_active" in data.columns:
                X_cols.append("is_discount_active")
            
            # Add time trend if date is available
            if "date" in data.columns:
                data["time_trend"] = (
                    data["date"] - data["date"].min()
                ).dt.days / 30  # Months
                X_cols.append("time_trend")
        
        X = data[X_cols].fillna(0)
        X = add_constant(X)
        y = data["log_quantity"]
        
        # Run OLS regression
        try:
            model = OLS(y, X)
            result = model.fit()
            
            self.model_result = result
            
            # Extract elasticity (coefficient on log_price)
            elasticity = result.params["log_price"]
            std_error = result.bse["log_price"]
            p_value = result.pvalues["log_price"]
            conf_int = result.conf_int(alpha=0.05)
            
            return {
                "elasticity": float(elasticity),
                "standard_error": float(std_error),
                "p_value": float(p_value),
                "conf_int_lower": float(conf_int.loc["log_price", 0]),
                "conf_int_upper": float(conf_int.loc["log_price", 1]),
                "r_squared": float(result.rsquared),
                "n_obs": int(result.nobs),
                "elastic": abs(elasticity) > 1.0,
                "interpretation": self._interpret_elasticity(elasticity),
            }
        except Exception as e:
            logger.error(f"Log-log regression failed: {str(e)}")
            return {"elasticity": None, "error": str(e)}
    
    def _interpret_elasticity(self, elasticity: float) -> str:
        """
        Interpret elasticity value
        
        Args:
            elasticity: Elasticity value
        
        Returns:
            Human-readable interpretation
        """
        if elasticity is None:
            return "Unknown"
        
        abs_e = abs(elasticity)
        
        if abs_e > 1.0:
            category = "Elastic"
            meaning = "Demand is sensitive to price changes"
        elif abs_e < 1.0:
            category = "Inelastic"
            meaning = "Demand is insensitive to price changes"
        else:
            category = "Unit elastic"
            meaning = "Demand changes proportionally with price"
        
        direction = "inverse" if elasticity < 0 else "direct"
        
        return f"{category} ({direction}): {meaning}"
    
    def recommend_optimal_price(
        self,
        current_price: float,
        cost_per_player: float = 0.0,
    ) -> Dict:
        """
        Recommend optimal price to maximize revenue
        
        Args:
            current_price: Current price
            cost_per_player: Variable cost per player (for profit optimization)
        
        Returns:
            Dictionary with optimal price recommendation
        """
        if self.elasticity is None:
            return {"error": "Elasticity must be calculated first"}
        
        # For elastic demand (|E| > 1), lower prices increase revenue
        # For inelastic demand (|E| < 1), higher prices increase revenue
        
        if abs(self.elasticity) > 1.0:
            # Elastic: recommend price decrease
            recommended_change_pct = -10  # 10% decrease
            direction = "decrease"
        else:
            # Inelastic: recommend price increase
            recommended_change_pct = 10  # 10% increase
            direction = "increase"
        
        optimal_price = current_price * (1 + recommended_change_pct / 100)
        
        # Estimate revenue impact
        # ΔQ ≈ E × (ΔP/P) × Q
        # ΔRevenue = (P + ΔP)(Q + ΔQ) - PQ
        
        price_change_pct = recommended_change_pct / 100
        quantity_change_pct = self.elasticity * price_change_pct
        
        return {
            "current_price": float(current_price),
            "optimal_price": float(optimal_price),
            "price_change_pct": float(recommended_change_pct),
            "direction": direction,
            "expected_quantity_change_pct": float(quantity_change_pct * 100),
            "elasticity": float(self.elasticity),
            "reasoning": (
                f"Given elasticity of {self.elasticity:.2f}, "
                f"a {abs(recommended_change_pct)}% price {direction} "
                f"should increase revenue."
            ),
        }


def calculate_elasticity_heatmap(
    data: pd.DataFrame,
    price_col: str = "current_price",
    quantity_col: str = "avg_players",
    row_groupby: str = "genre_name",
    col_groupby: Optional[str] = None,
) -> pd.DataFrame:
    """
    Calculate elasticity heatmap across two dimensions
    
    Args:
        data: Input DataFrame
        price_col: Price column name
        quantity_col: Quantity column name
        row_groupby: Row dimension (e.g., genre)
        col_groupby: Optional column dimension (e.g., price tier)
    
    Returns:
        DataFrame with elasticity values in heatmap format
    """
    if col_groupby is None:
        # Single dimension: just calculate by row_groupby
        model = PriceElasticityModel(data, price_col, quantity_col)
        results = model.calculate_arc_elasticity(group_by=row_groupby)
        
        if "by_group" in results:
            elasticities = results["by_group"]["elasticities"]
            df = pd.DataFrame([
                {
                    row_groupby: group,
                    "elasticity": values["elasticity"],
                }
                for group, values in elasticities.items()
            ])
            return df
        else:
            return pd.DataFrame()
    
    else:
        # Two dimensions: create heatmap
        heatmap_data = []
        
        row_groups = data[row_groupby].unique()
        col_groups = data[col_groupby].unique()
        
        for row_group in row_groups:
            for col_group in col_groups:
                group_data = data[
                    (data[row_groupby] == row_group) &
                    (data[col_groupby] == col_group)
                ]
                
                if len(group_data) < 5:
                    continue
                
                model = PriceElasticityModel(group_data, price_col, quantity_col)
                result = model.calculate_arc_elasticity()
                
                if "overall" in result and result["overall"]["elasticity"] is not None:
                    heatmap_data.append({
                        row_groupby: row_group,
                        col_groupby: col_group,
                        "elasticity": result["overall"]["elasticity"],
                    })
        
        df = pd.DataFrame(heatmap_data)
        
        if len(df) > 0:
            # Pivot to heatmap format
            heatmap = df.pivot(
                index=row_groupby,
                columns=col_groupby,
                values="elasticity",
            )
            return heatmap
        else:
            return pd.DataFrame()


def run_elasticity_analysis(
    player_price_data: pd.DataFrame,
    method: str = "log_log",
    group_by: Optional[str] = "genre_name",
) -> Dict:
    """
    Run complete price elasticity analysis
    
    Args:
        player_price_data: DataFrame with price and player data
        method: Method to use ('arc' or 'log_log')
        group_by: Optional column to group analysis
    
    Returns:
        Dictionary with elasticity analysis results
    """
    model = PriceElasticityModel(player_price_data)
    
    if method == "arc":
        results = model.calculate_arc_elasticity(group_by=group_by)
    elif method == "log_log":
        results = model.calculate_log_log_elasticity(
            include_controls=True,
            group_by=group_by,
        )
    else:
        raise ValueError(f"Unknown method: {method}")
    
    # Generate heatmap if grouping is used
    heatmap = None
    if group_by:
        try:
            heatmap_df = calculate_elasticity_heatmap(
                player_price_data,
                row_groupby=group_by,
            )
            heatmap = heatmap_df.to_dict() if not heatmap_df.empty else None
        except Exception as e:
            logger.warning(f"Heatmap generation failed: {str(e)}")
    
    # Compile results
    output = {
        "method": method,
        "elasticity_results": results,
        "heatmap": heatmap,
        "diagnostics": {
            "n_observations": len(player_price_data),
            "group_by": group_by,
        },
    }
    
    logger.info(f"Elasticity analysis complete: method={method}, group_by={group_by}")
    
    return output
