"""
Hybrid Merge Strategy
Combines data from SteamSpy, SteamCharts, and Steam Store
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, date
import pandas as pd

logger = logging.getLogger(__name__)


class DataMerger:
    """
    Merges data from multiple sources using a hybrid strategy
    
    Merge Strategy:
    - SteamSpy: Authoritative for game metadata and discovery
    - SteamCharts: Authoritative for player counts
    - Steam Store: Authoritative for pricing and release info
    """

    def merge_game_data(
        self,
        steamspy_data: Dict[str, List[Dict[str, Any]]],
        steamcharts_data: List[Dict[str, Any]],
        steam_store_data: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """
        Merge data from all three sources
        
        Args:
            steamspy_data: Transformed data from SteamSpyClient
            steamcharts_data: Transformed data from SteamChartsScraper
            steam_store_data: Transformed data from SteamStoreClient
            
        Returns:
            Dictionary with merged data ready for database loading
        """
        logger.info("Starting data merge process...")
        
        # Extract components
        steamspy_games = steamspy_data.get("games", [])
        steamspy_tags = steamspy_data.get("tags", [])
        steamspy_genres = steamspy_data.get("genres", [])
        steamspy_raw = steamspy_data.get("raw_games", [])
        
        steamcharts_facts = steamcharts_data
        
        steam_store_pricing = steam_store_data.get("pricing_facts", [])
        steam_store_updates = steam_store_data.get("game_updates", [])
        
        # Step 1: Merge game metadata (SteamSpy + Steam Store)
        merged_games = self._merge_game_metadata(steamspy_games, steam_store_updates)
        
        # Step 2: Create fact table records (SteamCharts + Steam Store pricing)
        merged_facts = self._merge_fact_records(steamcharts_facts, steam_store_pricing)
        
        # Step 3: Create bridge table records (game-tag relationships)
        bridge_records = self._create_bridge_records(steamspy_raw)
        
        logger.info(f"Merge complete: {len(merged_games)} games, "
                   f"{len(merged_facts)} fact records, "
                   f"{len(bridge_records)} bridge records")
        
        return {
            "dim_game": merged_games,
            "dim_tag": steamspy_tags,
            "dim_genre": steamspy_genres,
            "fact_player_price": merged_facts,
            "bridge_game_tag": bridge_records,
        }

    def _merge_game_metadata(
        self,
        steamspy_games: List[Dict[str, Any]],
        steam_store_updates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge game metadata from SteamSpy and Steam Store
        Steam Store is authoritative for pricing and release info
        
        Args:
            steamspy_games: Games from SteamSpy
            steam_store_updates: Metadata updates from Steam Store
            
        Returns:
            Merged game records
        """
        # Convert to DataFrames for easier merging
        df_steamspy = pd.DataFrame(steamspy_games)
        df_store = pd.DataFrame(steam_store_updates)
        
        if df_steamspy.empty:
            return []
        
        if not df_store.empty:
            # Left join: Keep all SteamSpy games, add Steam Store data where available
            df_merged = df_steamspy.merge(
                df_store,
                on="appid",
                how="left",
                suffixes=("", "_store")
            )
            
            # Steam Store is authoritative for these fields
            for field in ["is_free", "release_date", "developer", "publisher"]:
                store_field = f"{field}_store"
                if store_field in df_merged.columns:
                    # Update with Store data if available (not null)
                    df_merged[field] = df_merged[store_field].combine_first(df_merged[field])
                    df_merged.drop(columns=[store_field], inplace=True)
        else:
            df_merged = df_steamspy
        
        # Convert back to list of dicts
        merged_games = df_merged.to_dict('records')
        
        return merged_games

    def _merge_fact_records(
        self,
        steamcharts_facts: List[Dict[str, Any]],
        steam_store_pricing: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge fact records from SteamCharts and Steam Store
        
        Args:
            steamcharts_facts: Player count facts from SteamCharts
            steam_store_pricing: Pricing facts from Steam Store
            
        Returns:
            Merged fact table records
        """
        if not steamcharts_facts:
            return []
        
        # Convert to DataFrames
        df_charts = pd.DataFrame(steamcharts_facts)
        
        if not steam_store_pricing:
            # No pricing data, return charts data as-is
            return steamcharts_facts
        
        df_pricing = pd.DataFrame(steam_store_pricing)
        
        # For pricing, we don't have temporal data, so we apply latest pricing to all records
        # In a production system, you'd track pricing history
        # For now: left join on appid
        df_merged = df_charts.merge(
            df_pricing,
            on="appid",
            how="left"
        )
        
        # Convert back to list of dicts
        merged_facts = df_merged.to_dict('records')
        
        return merged_facts

    def _create_bridge_records(
        self,
        steamspy_raw: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Create bridge table records for game-tag relationships
        
        Args:
            steamspy_raw: Raw SteamSpy data with tags
            
        Returns:
            List of bridge records (appid, tag_name)
        """
        bridge_records = []
        
        for game in steamspy_raw:
            appid = game.get("appid")
            tags = game.get("tags", {})
            
            if not appid or not tags:
                continue
            
            for tag_name in tags.keys():
                bridge_records.append({
                    "appid": appid,
                    "tag_name": tag_name
                })
        
        return bridge_records

    def deduplicate_facts(
        self,
        fact_records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate fact records based on (appid, month, year)
        
        Args:
            fact_records: List of fact table records
            
        Returns:
            Deduplicated fact records
        """
        if not fact_records:
            return []
        
        df = pd.DataFrame(fact_records)
        
        # Deduplicate on (appid, month, year) - keep first occurrence
        if all(col in df.columns for col in ["appid", "month", "year"]):
            df_deduped = df.drop_duplicates(subset=["appid", "month", "year"], keep="first")
            logger.info(f"Deduplicated {len(df) - len(df_deduped)} fact records")
            return df_deduped.to_dict('records')
        
        return fact_records
