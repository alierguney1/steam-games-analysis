"""
SteamSpy API Client
Fetches game metadata from SteamSpy API
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.ingestion.base_scraper import BaseScraper
from app.config import settings


logger = logging.getLogger(__name__)


class SteamSpyClient(BaseScraper):
    """
    SteamSpy API client with special rate limiting
    
    Rate limits:
    - /all endpoint: 60 seconds between requests
    - /appdetails endpoint: 1 second between requests
    """

    def __init__(self):
        # Default to 1 request per second for most endpoints
        super().__init__(
            rate_limit_requests=1,
            rate_limit_period=1.0
        )
        self._base_url = settings.STEAMSPY_API_URL

    async def fetch_all_games(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetch all games from SteamSpy
        WARNING: This endpoint has a 60-second rate limit!
        
        Args:
            limit: Optional limit on number of games to return
            
        Returns:
            Dictionary mapping appid to game data
        """
        logger.info("Fetching all games from SteamSpy (60s rate limit applies)")
        
        params = {"request": "all"}
        data = await self._rate_limited_fetch(self._base_url, params=params)
        
        # The /all endpoint requires 60 seconds before next request
        logger.info("Waiting 60 seconds after /all request (SteamSpy requirement)")
        
        if limit:
            # Convert to list, limit, and convert back to dict
            items = list(data.items())[:limit]
            data = dict(items)
        
        logger.info(f"Fetched {len(data)} games from SteamSpy")
        return data

    async def fetch_game_detail(self, appid: int) -> Dict[str, Any]:
        """
        Fetch detailed information for a specific game
        
        Args:
            appid: Steam application ID
            
        Returns:
            Game detail data
        """
        params = {
            "request": "appdetails",
            "appid": appid
        }
        
        data = await self._rate_limited_fetch(self._base_url, params=params)
        return data

    async def fetch(self, appids: Optional[List[int]] = None, fetch_all: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch game data from SteamSpy
        
        Args:
            appids: List of Steam application IDs to fetch
            fetch_all: If True, fetch all games (ignores appids parameter)
            
        Returns:
            List of game data dictionaries
        """
        if fetch_all:
            all_games = await self.fetch_all_games()
            return [
                {"appid": int(appid), **data}
                for appid, data in all_games.items()
            ]
        
        if not appids:
            raise ValueError("Must provide appids or set fetch_all=True")
        
        games = []
        for appid in appids:
            try:
                data = await self.fetch_game_detail(appid)
                data["appid"] = appid
                games.append(data)
            except Exception as e:
                logger.error(f"Failed to fetch game {appid}: {e}")
                continue
        
        return games

    def parse(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse raw SteamSpy data into structured format
        
        Args:
            raw_data: List of raw game data from SteamSpy
            
        Returns:
            List of parsed game dictionaries
        """
        parsed_games = []
        
        for game in raw_data:
            try:
                parsed_game = {
                    "appid": game.get("appid"),
                    "name": game.get("name"),
                    "developer": game.get("developer"),
                    "publisher": game.get("publisher"),
                    "positive_reviews": game.get("positive", 0),
                    "negative_reviews": game.get("negative", 0),
                    "owners_min": self._parse_owners(game.get("owners"), "min"),
                    "owners_max": self._parse_owners(game.get("owners"), "max"),
                    "average_forever": game.get("average_forever", 0),
                    "average_2weeks": game.get("average_2weeks", 0),
                    "median_forever": game.get("median_forever", 0),
                    "median_2weeks": game.get("median_2weeks", 0),
                    "ccu": game.get("ccu", 0),  # Current concurrent users
                    "price": game.get("price", 0),
                    "initialprice": game.get("initialprice", 0),
                    "discount": game.get("discount", 0),
                    "tags": game.get("tags", {}),
                    "genres": game.get("genre", ""),
                    "languages": game.get("languages", ""),
                }
                parsed_games.append(parsed_game)
            except Exception as e:
                logger.error(f"Failed to parse game {game.get('appid')}: {e}")
                continue
        
        return parsed_games

    def _parse_owners(self, owners_str: str, bound: str) -> Optional[int]:
        """
        Parse SteamSpy owners string (e.g., "10,000 .. 20,000")
        
        Args:
            owners_str: String like "10,000 .. 20,000"
            bound: "min" or "max"
            
        Returns:
            Integer value of min or max owners
        """
        if not owners_str:
            return None
        
        try:
            parts = owners_str.replace(",", "").split("..")
            if len(parts) == 2:
                if bound == "min":
                    return int(parts[0].strip())
                else:
                    return int(parts[1].strip())
            return None
        except:
            return None

    def transform(self, parsed_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Transform parsed data into database-ready format
        
        Args:
            parsed_data: List of parsed game dictionaries
            
        Returns:
            Dictionary with separate lists for dim_game, dim_tag, and bridge records
        """
        games = []
        tags_set = set()
        genres_set = set()
        
        for game in parsed_data:
            # Prepare dim_game record
            game_record = {
                "appid": game["appid"],
                "name": game["name"],
                "developer": game["developer"],
                "publisher": game["publisher"],
                "steamspy_owners_min": game["owners_min"],
                "steamspy_owners_max": game["owners_max"],
                "positive_reviews": game["positive_reviews"],
                "negative_reviews": game["negative_reviews"],
            }
            games.append(game_record)
            
            # Collect unique tags
            if game.get("tags"):
                for tag_name in game["tags"].keys():
                    tags_set.add(tag_name)
            
            # Collect unique genres
            if game.get("genres"):
                for genre in game["genres"].split(","):
                    genre = genre.strip()
                    if genre:
                        genres_set.add(genre)
        
        # Prepare tag and genre records
        tags = [{"tag_name": tag} for tag in tags_set]
        genres = [{"genre_name": genre} for genre in genres_set]
        
        return {
            "games": games,
            "tags": tags,
            "genres": genres,
            "raw_games": parsed_data  # Keep raw data for bridge table creation
        }
