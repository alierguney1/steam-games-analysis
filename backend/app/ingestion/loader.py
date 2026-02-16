"""
PostgreSQL Data Loader
Handles bulk upsert operations for ingested data
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from sqlalchemy import select, insert, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.db.models import DimGame, DimGenre, DimTag, DimDate, FactPlayerPrice, BridgeGameTag

logger = logging.getLogger(__name__)


class DataLoader:
    """
    Loads merged data into PostgreSQL database
    Uses bulk upsert operations for efficiency
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize loader with database session

        Args:
            session: Async SQLAlchemy session
        """
        self.session = session

    async def load_all(self, merged_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Load all merged data into database

        Args:
            merged_data: Dictionary with all merged data

        Returns:
            Dictionary with counts of inserted/updated records
        """
        logger.info("Starting database load...")

        stats = {}

        # Load dimension tables first (order matters for foreign keys)
        stats["genres"] = await self.load_genres(merged_data.get("dim_genre", []))
        stats["tags"] = await self.load_tags(merged_data.get("dim_tag", []))
        stats["games"] = await self.load_games(merged_data.get("dim_game", []))

        # Load fact table
        stats["facts"] = await self.load_facts(merged_data.get("fact_player_price", []))

        # Load bridge table
        stats["bridges"] = await self.load_bridges(merged_data.get("bridge_game_tag", []))

        # Commit transaction
        await self.session.commit()

        logger.info(f"Database load complete: {stats}")
        return stats

    async def load_genres(self, genres: List[Dict[str, Any]]) -> int:
        """
        Load genre records with upsert

        Args:
            genres: List of genre dictionaries

        Returns:
            Number of genres processed
        """
        if not genres:
            return 0

        count = 0
        for genre in genres:
            # Use PostgreSQL INSERT ... ON CONFLICT DO NOTHING
            stmt = (
                pg_insert(DimGenre)
                .values(genre_name=genre["genre_name"])
                .on_conflict_do_nothing(index_elements=["genre_name"])
            )

            await self.session.execute(stmt)
            count += 1

        logger.info(f"Loaded {count} genres")
        return count

    async def load_tags(self, tags: List[Dict[str, Any]]) -> int:
        """
        Load tag records with upsert

        Args:
            tags: List of tag dictionaries

        Returns:
            Number of tags processed
        """
        if not tags:
            return 0

        count = 0
        for tag in tags:
            stmt = (
                pg_insert(DimTag)
                .values(tag_name=tag["tag_name"])
                .on_conflict_do_nothing(index_elements=["tag_name"])
            )

            await self.session.execute(stmt)
            count += 1

        logger.info(f"Loaded {count} tags")
        return count

    async def load_games(self, games: List[Dict[str, Any]]) -> int:
        """
        Load game records with upsert

        Args:
            games: List of game dictionaries

        Returns:
            Number of games processed
        """
        if not games:
            return 0

        count = 0
        for game in games:
            # Prepare values (handle None/NaN values)
            values = {
                "appid": game["appid"],
                "name": game.get("name", "Unknown"),
                "developer": game.get("developer"),
                "publisher": game.get("publisher"),
                "release_date": game.get("release_date"),
                "is_free": game.get("is_free", False),
                "steamspy_owners_min": game.get("steamspy_owners_min"),
                "steamspy_owners_max": game.get("steamspy_owners_max"),
                "positive_reviews": game.get("positive_reviews", 0),
                "negative_reviews": game.get("negative_reviews", 0),
                "updated_at": datetime.utcnow(),
            }

            # Clean None/NaN values
            values = {k: v for k, v in values.items() if v is not None and str(v) != "nan"}

            # Upsert: INSERT ... ON CONFLICT DO UPDATE
            stmt = pg_insert(DimGame).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["appid"],
                set_={
                    **{k: v for k, v in values.items() if k != "appid"},
                },
            )

            await self.session.execute(stmt)
            count += 1

        logger.info(f"Loaded {count} games")
        return count

    async def load_facts(self, facts: List[Dict[str, Any]]) -> int:
        """
        Load fact table records

        Args:
            facts: List of fact dictionaries

        Returns:
            Number of facts processed
        """
        if not facts:
            return 0

        count = 0
        for fact in facts:
            # Get game_id from appid
            game_id = await self._get_game_id(fact["appid"])
            if not game_id:
                logger.warning(f"Game not found for appid {fact['appid']}, skipping fact")
                continue

            # Get date_id from month/year
            date_id = await self._get_or_create_date_id(fact.get("year"), fact.get("month"))
            if not date_id:
                logger.warning(f"Could not create date for {fact.get('year')}/{fact.get('month')}")
                continue

            # Prepare values
            values = {
                "game_id": game_id,
                "date_id": date_id,
                "concurrent_players_avg": fact.get("concurrent_players_avg"),
                "concurrent_players_peak": fact.get("concurrent_players_peak"),
                "gain_pct": fact.get("gain_pct"),
                "avg_players_month": fact.get("avg_players_month"),
                "peak_players_month": fact.get("peak_players_month"),
                "current_price": fact.get("current_price"),
                "original_price": fact.get("original_price"),
                "discount_pct": fact.get("discount_pct"),
                "is_discount_active": fact.get("is_discount_active", False),
            }

            # Clean None/NaN values
            values = {k: v for k, v in values.items() if v is not None and str(v) != "nan"}

            # Insert (deduplicate check should have been done in merger)
            stmt = insert(FactPlayerPrice).values(**values)
            await self.session.execute(stmt)
            count += 1

        logger.info(f"Loaded {count} fact records")
        return count

    async def load_bridges(self, bridges: List[Dict[str, Any]]) -> int:
        """
        Load bridge table records (game-tag relationships)

        Args:
            bridges: List of bridge dictionaries

        Returns:
            Number of bridge records processed
        """
        if not bridges:
            return 0

        count = 0
        for bridge in bridges:
            # Get game_id and tag_id
            game_id = await self._get_game_id(bridge["appid"])
            tag_id = await self._get_tag_id(bridge["tag_name"])

            if not game_id or not tag_id:
                continue

            # Insert with conflict ignore
            stmt = (
                pg_insert(BridgeGameTag)
                .values(game_id=game_id, tag_id=tag_id)
                .on_conflict_do_nothing(index_elements=["game_id", "tag_id"])
            )

            await self.session.execute(stmt)
            count += 1

        logger.info(f"Loaded {count} bridge records")
        return count

    async def _get_game_id(self, appid: int) -> Optional[int]:
        """Get game_id from appid"""
        result = await self.session.execute(select(DimGame.game_id).where(DimGame.appid == appid))
        row = result.first()
        return row[0] if row else None

    async def _get_tag_id(self, tag_name: str) -> Optional[int]:
        """Get tag_id from tag_name"""
        result = await self.session.execute(
            select(DimTag.tag_id).where(DimTag.tag_name == tag_name)
        )
        row = result.first()
        return row[0] if row else None

    async def _get_or_create_date_id(
        self, year: Optional[int], month: Optional[int]
    ) -> Optional[int]:
        """
        Get or create date_id from year and month
        Creates the first day of the month
        """
        if not year or not month:
            return None

        try:
            full_date = date(year, month, 1)
        except Exception:
            return None

        # Try to get existing date
        result = await self.session.execute(
            select(DimDate.date_id).where(DimDate.full_date == full_date)
        )
        row = result.first()

        if row:
            return row[0]

        # Create new date record
        day_of_week = full_date.weekday()
        is_weekend = day_of_week >= 5
        quarter = (month - 1) // 3 + 1

        stmt = (
            pg_insert(DimDate)
            .values(
                full_date=full_date,
                year=year,
                quarter=quarter,
                month=month,
                day=1,
                day_of_week=day_of_week,
                is_weekend=is_weekend,
                is_steam_sale_period=False,  # TODO: Update with actual sale periods
            )
            .returning(DimDate.date_id)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one()
