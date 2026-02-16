"""
SteamCharts Web Scraper
Scrapes player count history from SteamCharts.com
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup

from app.ingestion.base_scraper import BaseScraper
from app.config import settings


logger = logging.getLogger(__name__)


class SteamChartsScraper(BaseScraper):
    """
    SteamCharts web scraper for historical player count data
    Respects robots.txt and uses polite scraping practices
    """

    def __init__(self):
        super().__init__(
            rate_limit_requests=1,
            rate_limit_period=2.0  # 2 seconds between requests to be polite
        )
        self._base_url = settings.STEAMCHARTS_BASE_URL

    async def fetch_game_history(self, appid: int) -> str:
        """
        Fetch player count history HTML for a specific game
        
        Args:
            appid: Steam application ID
            
        Returns:
            HTML content as string
        """
        url = f"{self._base_url}/app/{appid}"
        logger.debug(f"Fetching SteamCharts data for appid {appid}")
        
        try:
            data = await self._rate_limited_fetch(url)
            return data.get("text", "")
        except Exception as e:
            logger.error(f"Failed to fetch SteamCharts for appid {appid}: {e}")
            return ""

    async def fetch(self, appids: List[int]) -> List[Dict[str, Any]]:
        """
        Fetch player count history for multiple games
        
        Args:
            appids: List of Steam application IDs
            
        Returns:
            List of dictionaries with appid and HTML content
        """
        results = []
        for appid in appids:
            html = await self.fetch_game_history(appid)
            results.append({
                "appid": appid,
                "html": html
            })
        
        return results

    def parse(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse HTML to extract player count data
        
        Args:
            raw_data: List of dictionaries with appid and HTML content
            
        Returns:
            List of parsed player count records
        """
        all_records = []
        
        for item in raw_data:
            appid = item["appid"]
            html = item["html"]
            
            if not html:
                continue
            
            try:
                records = self._parse_game_html(appid, html)
                all_records.extend(records)
            except Exception as e:
                logger.error(f"Failed to parse SteamCharts HTML for appid {appid}: {e}")
                continue
        
        return all_records

    def _parse_game_html(self, appid: int, html: str) -> List[Dict[str, Any]]:
        """
        Parse HTML for a single game to extract player count table
        
        Args:
            appid: Steam application ID
            html: HTML content
            
        Returns:
            List of monthly player count records
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # Find the main player count table
        table = soup.find('table', class_='common-table')
        
        if not table:
            logger.warning(f"No player count table found for appid {appid}")
            return []
        
        records = []
        rows = table.find_all('tr')[1:]  # Skip header row
        
        for row in rows:
            cells = row.find_all('td')
            
            if len(cells) < 5:
                continue
            
            try:
                # Parse table cells
                # Format: Month | Avg. Players | Gain | % Gain | Peak Players
                month_year_str = cells[0].text.strip()
                avg_players_str = cells[1].text.strip()
                gain_str = cells[2].text.strip()
                gain_pct_str = cells[3].text.strip()
                peak_players_str = cells[4].text.strip()
                
                # Parse month/year (e.g., "January 2024")
                month_year = self._parse_month_year(month_year_str)
                if not month_year:
                    continue
                
                # Parse player counts (remove commas)
                avg_players = self._parse_number(avg_players_str)
                peak_players = self._parse_number(peak_players_str)
                gain = self._parse_number(gain_str, allow_negative=True)
                gain_pct = self._parse_percentage(gain_pct_str)
                
                record = {
                    "appid": appid,
                    "month": month_year["month"],
                    "year": month_year["year"],
                    "avg_players": avg_players,
                    "peak_players": peak_players,
                    "gain": gain,
                    "gain_pct": gain_pct,
                }
                records.append(record)
                
            except Exception as e:
                logger.debug(f"Failed to parse row for appid {appid}: {e}")
                continue
        
        logger.info(f"Parsed {len(records)} monthly records for appid {appid}")
        return records

    def _parse_month_year(self, month_year_str: str) -> Optional[Dict[str, int]]:
        """
        Parse month/year string like "January 2024"
        
        Args:
            month_year_str: String like "January 2024"
            
        Returns:
            Dictionary with month and year integers
        """
        try:
            dt = datetime.strptime(month_year_str, "%B %Y")
            return {
                "month": dt.month,
                "year": dt.year
            }
        except:
            return None

    def _parse_number(self, num_str: str, allow_negative: bool = False) -> Optional[int]:
        """
        Parse number string (remove commas, handle signs)
        
        Args:
            num_str: String like "1,234" or "-1,234" or "N/A"
            allow_negative: Whether to allow negative numbers
            
        Returns:
            Integer value or None
        """
        if not num_str or num_str == "N/A":
            return None
        
        try:
            # Remove commas and strip
            clean_str = num_str.replace(",", "").strip()
            
            # Handle sign
            if clean_str.startswith("+"):
                clean_str = clean_str[1:]
            elif clean_str.startswith("-") and not allow_negative:
                return None
            
            return int(float(clean_str))
        except:
            return None

    def _parse_percentage(self, pct_str: str) -> Optional[float]:
        """
        Parse percentage string like "+5.2%" or "-10.5%"
        
        Args:
            pct_str: String like "+5.2%"
            
        Returns:
            Float value (5.2, not 0.052) or None
        """
        if not pct_str or pct_str == "N/A":
            return None
        
        try:
            # Remove % sign and +/- prefix
            clean_str = pct_str.replace("%", "").replace("+", "").strip()
            return float(clean_str)
        except:
            return None

    def transform(self, parsed_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform parsed data into database-ready fact table records
        
        Args:
            parsed_data: List of parsed monthly player count records
            
        Returns:
            List of fact_player_price records (player metrics only)
        """
        fact_records = []
        
        for record in parsed_data:
            # Create fact table record with player metrics
            fact_record = {
                "appid": record["appid"],
                "month": record["month"],
                "year": record["year"],
                "concurrent_players_avg": record["avg_players"],
                "concurrent_players_peak": record["peak_players"],
                "gain_pct": record["gain_pct"],
                "avg_players_month": record["avg_players"],
                "peak_players_month": record["peak_players"],
            }
            fact_records.append(fact_record)
        
        return fact_records
