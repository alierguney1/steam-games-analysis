"""
Base Scraper Abstract Class
Provides rate-limiting, retry logic, and async HTTP session management
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from aiohttp import ClientSession, ClientTimeout, ClientError
from app.config import settings


logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers
    Implements rate-limiting, retry logic, and connection pooling
    """

    def __init__(
        self,
        rate_limit_requests: int = None,
        rate_limit_period: float = None,
        max_retries: int = None,
        retry_backoff: float = None,
    ):
        """
        Initialize scraper with rate limiting and retry configuration

        Args:
            rate_limit_requests: Number of requests allowed per period
            rate_limit_period: Time period in seconds for rate limiting
            max_retries: Maximum number of retry attempts
            retry_backoff: Exponential backoff multiplier
        """
        self._rate_limit_requests = rate_limit_requests or settings.RATE_LIMIT_REQUESTS
        self._rate_limit_period = rate_limit_period or settings.RATE_LIMIT_PERIOD
        self._max_retries = max_retries or settings.MAX_RETRIES
        self._retry_backoff = retry_backoff or settings.RETRY_BACKOFF

        # Rate limiting semaphore
        self._semaphore = asyncio.Semaphore(self._rate_limit_requests)

        # HTTP session (will be initialized in context manager)
        self._session: Optional[ClientSession] = None

        # User agent for requests
        self._user_agent = settings.USER_AGENT

        # Request timeout
        self._timeout = ClientTimeout(total=settings.REQUEST_TIMEOUT)

    async def __aenter__(self):
        """Async context manager entry - initialize session"""
        self._session = ClientSession(
            timeout=self._timeout, headers={"User-Agent": self._user_agent}
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close session"""
        if self._session:
            await self._session.close()

    async def _rate_limited_fetch(
        self, url: str, params: Optional[Dict[str, Any]] = None, method: str = "GET", **kwargs
    ) -> Dict[str, Any]:
        """
        Fetch URL with rate limiting and retry logic

        Args:
            url: URL to fetch
            params: Query parameters
            method: HTTP method (GET, POST, etc.)
            **kwargs: Additional arguments to pass to aiohttp

        Returns:
            Response data as dictionary

        Raises:
            ClientError: If request fails after all retries
        """
        async with self._semaphore:
            for attempt in range(self._max_retries):
                try:
                    logger.debug(f"Fetching {url} (attempt {attempt + 1}/{self._max_retries})")

                    async with self._session.request(
                        method=method, url=url, params=params, **kwargs
                    ) as response:
                        response.raise_for_status()

                        # Try to parse as JSON first
                        try:
                            data = await response.json()
                        except Exception:
                            # If JSON parsing fails, return text
                            data = {"text": await response.text()}

                        # Rate limiting delay
                        await asyncio.sleep(self._rate_limit_period)

                        return data

                except ClientError as e:
                    if attempt == self._max_retries - 1:
                        logger.error(
                            f"Failed to fetch {url} after {self._max_retries} attempts: {e}"
                        )
                        raise

                    # Exponential backoff
                    wait_time = self._retry_backoff**attempt
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self._max_retries}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    await asyncio.sleep(wait_time)

    @abstractmethod
    async def fetch(self, **kwargs) -> Any:
        """
        Fetch data from source (must be implemented by subclass)

        Args:
            **kwargs: Source-specific parameters

        Returns:
            Raw data from source
        """
        pass

    @abstractmethod
    def parse(self, raw_data: Any) -> Any:
        """
        Parse raw data into structured format (must be implemented by subclass)

        Args:
            raw_data: Raw data from fetch()

        Returns:
            Parsed data structure
        """
        pass

    @abstractmethod
    def transform(self, parsed_data: Any) -> Any:
        """
        Transform parsed data into database-ready format (must be implemented by subclass)

        Args:
            parsed_data: Parsed data from parse()

        Returns:
            Database-ready records
        """
        pass
