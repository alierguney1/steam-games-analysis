"""
Steam Store API Client
Fetches pricing and discount information from Steam Store API
"""

import logging
from typing import Dict, List, Any, Optional

from app.ingestion.base_scraper import BaseScraper
from app.config import settings


logger = logging.getLogger(__name__)


class SteamStoreClient(BaseScraper):
    """
    Steam Store API client for pricing and discount data
    Supports batch requests (up to 200 appids at once)
    """

    def __init__(self):
        super().__init__(
            rate_limit_requests=1,
            rate_limit_period=1.5  # 1.5 seconds between batch requests
        )
        self._base_url = settings.STEAM_STORE_API_URL

    async def fetch_app_details(self, appid: int, country_code: str = "us") -> Dict[str, Any]:
        """
        Fetch detailed information for a single app
        
        Args:
            appid: Steam application ID
            country_code: Country code for regional pricing (default: us)
            
        Returns:
            App details including price information
        """
        params = {
            "appids": appid,
            "cc": country_code,
            "filters": "price_overview"
        }
        
        try:
            data = await self._rate_limited_fetch(self._base_url, params=params)
            return data
        except Exception as e:
            logger.error(f"Failed to fetch Steam Store data for appid {appid}: {e}")
            return {}

    async def fetch_batch(
        self,
        appids: List[int],
        batch_size: int = 200,
        country_code: str = "us"
    ) -> List[Dict[str, Any]]:
        """
        Fetch app details in batches
        
        Args:
            appids: List of Steam application IDs
            batch_size: Number of apps per batch (max 200)
            country_code: Country code for regional pricing
            
        Returns:
            List of app details
        """
        all_data = []
        
        # Process in batches
        for i in range(0, len(appids), batch_size):
            batch = appids[i:i + batch_size]
            logger.info(f"Fetching Steam Store batch {i // batch_size + 1} "
                       f"({len(batch)} apps)")
            
            for appid in batch:
                data = await self.fetch_app_details(appid, country_code)
                if data:
                    all_data.append({
                        "appid": appid,
                        "data": data
                    })
        
        return all_data

    async def fetch(self, appids: List[int], country_code: str = "us") -> List[Dict[str, Any]]:
        """
        Fetch pricing data for multiple games
        
        Args:
            appids: List of Steam application IDs
            country_code: Country code for regional pricing
            
        Returns:
            List of dictionaries with appid and pricing data
        """
        return await self.fetch_batch(appids, country_code=country_code)

    def parse(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse raw Steam Store API response
        
        Args:
            raw_data: List of raw API responses
            
        Returns:
            List of parsed pricing records
        """
        parsed_records = []
        
        for item in raw_data:
            appid = item["appid"]
            data = item["data"]
            
            try:
                # Navigate the nested structure: {appid: {success: bool, data: {...}}}
                app_data = data.get(str(appid), {})
                
                if not app_data.get("success"):
                    logger.debug(f"No success response for appid {appid}")
                    continue
                
                app_info = app_data.get("data", {})
                price_info = app_info.get("price_overview", {})
                
                if not price_info:
                    # Free game or no price info
                    parsed_record = {
                        "appid": appid,
                        "is_free": app_info.get("is_free", False),
                        "current_price": 0,
                        "original_price": 0,
                        "discount_pct": 0,
                        "is_discount_active": False,
                        "currency": "USD",
                    }
                else:
                    parsed_record = {
                        "appid": appid,
                        "is_free": False,
                        "current_price": price_info.get("final", 0) / 100.0,  # Convert cents to dollars
                        "original_price": price_info.get("initial", 0) / 100.0,
                        "discount_pct": price_info.get("discount_percent", 0),
                        "is_discount_active": price_info.get("discount_percent", 0) > 0,
                        "currency": price_info.get("currency", "USD"),
                    }
                
                # Additional metadata
                parsed_record.update({
                    "name": app_info.get("name", ""),
                    "type": app_info.get("type", ""),
                    "release_date": app_info.get("release_date", {}).get("date", ""),
                    "developers": app_info.get("developers", []),
                    "publishers": app_info.get("publishers", []),
                    "genres": [g.get("description", "") for g in app_info.get("genres", [])],
                    "categories": [c.get("description", "") for c in app_info.get("categories", [])],
                })
                
                parsed_records.append(parsed_record)
                
            except Exception as e:
                logger.error(f"Failed to parse Steam Store data for appid {appid}: {e}")
                continue
        
        return parsed_records

    def transform(self, parsed_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Transform parsed data into database-ready format
        
        Args:
            parsed_data: List of parsed pricing records
            
        Returns:
            Dictionary with pricing facts and updated game metadata
        """
        pricing_facts = []
        game_updates = []
        
        for record in parsed_data:
            # Pricing fact (for fact_player_price table)
            pricing_fact = {
                "appid": record["appid"],
                "current_price": record["current_price"],
                "original_price": record["original_price"],
                "discount_pct": record["discount_pct"],
                "is_discount_active": record["is_discount_active"],
            }
            pricing_facts.append(pricing_fact)
            
            # Game metadata updates (for dim_game table)
            if record.get("release_date"):
                try:
                    from datetime import datetime
                    release_date = datetime.strptime(record["release_date"], "%b %d, %Y").date()
                except Exception:
                    release_date = None
            else:
                release_date = None
            
            game_update = {
                "appid": record["appid"],
                "is_free": record["is_free"],
                "release_date": release_date,
                "developer": ", ".join(record.get("developers", []))[:500] if record.get("developers") else None,
                "publisher": ", ".join(record.get("publishers", []))[:500] if record.get("publishers") else None,
            }
            game_updates.append(game_update)
        
        return {
            "pricing_facts": pricing_facts,
            "game_updates": game_updates,
        }
