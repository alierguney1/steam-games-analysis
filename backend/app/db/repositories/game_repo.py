"""
Game Repository
CRUD operations for games
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, desc, asc
from sqlalchemy.orm import selectinload

from app.db.models import DimGame, BridgeGameTag, DimTag, FactPlayerPrice, DimGenre
from app.schemas.game import GameCreate, GameUpdate


class GameRepository:
    """Repository for game operations"""
    
    @staticmethod
    async def create_game(
        session: AsyncSession,
        game_data: GameCreate,
    ) -> DimGame:
        """
        Create a new game
        
        Args:
            session: Database session
            game_data: Game creation data
            
        Returns:
            Created game instance
        """
        game = DimGame(
            appid=game_data.appid,
            name=game_data.name,
            developer=game_data.developer,
            publisher=game_data.publisher,
            release_date=game_data.release_date,
            is_free=game_data.is_free,
            steamspy_owners_min=game_data.steamspy_owners_min,
            steamspy_owners_max=game_data.steamspy_owners_max,
            positive_reviews=game_data.positive_reviews,
            negative_reviews=game_data.negative_reviews,
        )
        
        session.add(game)
        await session.commit()
        await session.refresh(game)
        
        return game
    
    @staticmethod
    async def get_game_by_id(
        session: AsyncSession,
        game_id: int,
        include_tags: bool = False,
        include_recent_facts: bool = False,
    ) -> Optional[DimGame]:
        """
        Get game by ID with optional relationships
        
        Args:
            session: Database session
            game_id: Game ID
            include_tags: Whether to load tags
            include_recent_facts: Whether to load recent facts
            
        Returns:
            Game instance or None
        """
        query = select(DimGame).where(DimGame.game_id == game_id)
        
        if include_tags:
            query = query.options(
                selectinload(DimGame.tags).selectinload(BridgeGameTag.tag)
            )
        
        result = await session.execute(query)
        game = result.scalar_one_or_none()
        
        if game and include_recent_facts:
            # Load recent facts (last 12 months)
            cutoff_date = datetime.utcnow() - timedelta(days=365)
            facts_query = (
                select(FactPlayerPrice)
                .where(FactPlayerPrice.game_id == game_id)
                .join(FactPlayerPrice.date)
                .where(DimGame.created_at >= cutoff_date)
                .order_by(desc(FactPlayerPrice.date_id))
                .limit(12)
            )
            facts_result = await session.execute(facts_query)
            game.recent_facts = facts_result.scalars().all()
        
        return game
    
    @staticmethod
    async def get_game_by_appid(
        session: AsyncSession,
        appid: int,
    ) -> Optional[DimGame]:
        """
        Get game by Steam App ID
        
        Args:
            session: Database session
            appid: Steam App ID
            
        Returns:
            Game instance or None
        """
        result = await session.execute(
            select(DimGame).where(DimGame.appid == appid)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_game(
        session: AsyncSession,
        game_id: int,
        game_data: GameUpdate,
    ) -> Optional[DimGame]:
        """
        Update game
        
        Args:
            session: Database session
            game_id: Game ID
            game_data: Update data
            
        Returns:
            Updated game or None
        """
        game = await GameRepository.get_game_by_id(session, game_id)
        if not game:
            return None
        
        # Update only provided fields
        update_data = game_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(game, field, value)
        
        game.updated_at = datetime.utcnow()
        
        await session.commit()
        await session.refresh(game)
        
        return game
    
    @staticmethod
    async def delete_game(
        session: AsyncSession,
        game_id: int,
    ) -> bool:
        """
        Delete game
        
        Args:
            session: Database session
            game_id: Game ID
            
        Returns:
            True if deleted, False if not found
        """
        game = await GameRepository.get_game_by_id(session, game_id)
        if not game:
            return False
        
        await session.delete(game)
        await session.commit()
        
        return True
    
    @staticmethod
    async def list_games(
        session: AsyncSession,
        query: Optional[str] = None,
        genre: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_free: Optional[bool] = None,
        min_players: Optional[int] = None,
        page: int = 1,
        page_size: int = 30,
        sort_by: str = "name",
        sort_order: str = "asc",
    ) -> tuple[List[DimGame], int]:
        """
        List games with filtering, sorting and pagination
        
        Args:
            session: Database session
            query: Search query (name, developer, publisher)
            genre: Filter by genre
            tags: Filter by tags
            is_free: Filter by free/paid
            min_players: Minimum average players
            page: Page number
            page_size: Items per page
            sort_by: Sort field
            sort_order: Sort order (asc/desc)
            
        Returns:
            Tuple of (games list, total count)
        """
        # Base query
        stmt = select(DimGame)
        count_stmt = select(func.count()).select_from(DimGame)
        
        # Apply filters
        filters = []
        
        if query:
            search_filter = or_(
                DimGame.name.ilike(f"%{query}%"),
                DimGame.developer.ilike(f"%{query}%"),
                DimGame.publisher.ilike(f"%{query}%"),
            )
            filters.append(search_filter)
        
        if is_free is not None:
            filters.append(DimGame.is_free == is_free)
        
        if filters:
            stmt = stmt.where(and_(*filters))
            count_stmt = count_stmt.where(and_(*filters))
        
        # Genre filter (requires join with facts)
        if genre:
            stmt = stmt.join(FactPlayerPrice).join(DimGenre).where(
                DimGenre.genre_name == genre
            )
            count_stmt = count_stmt.join(FactPlayerPrice).join(DimGenre).where(
                DimGenre.genre_name == genre
            )
        
        # Tags filter (requires join with bridge table)
        if tags:
            stmt = stmt.join(BridgeGameTag).join(DimTag).where(
                DimTag.tag_name.in_(tags)
            )
            count_stmt = count_stmt.join(BridgeGameTag).join(DimTag).where(
                DimTag.tag_name.in_(tags)
            )
        
        # Min players filter (requires subquery for recent average)
        if min_players:
            # Use a lateral join to get recent average players
            recent_avg_subquery = (
                select(func.avg(FactPlayerPrice.concurrent_players_avg))
                .where(FactPlayerPrice.game_id == DimGame.game_id)
                .order_by(desc(FactPlayerPrice.date_id))
                .limit(3)
                .scalar_subquery()
            )
            stmt = stmt.where(recent_avg_subquery >= min_players)
        
        # Get total count
        total_result = await session.execute(count_stmt)
        total = total_result.scalar()
        
        # Apply sorting
        sort_column = getattr(DimGame, sort_by, DimGame.name)
        if sort_order == "desc":
            stmt = stmt.order_by(desc(sort_column))
        else:
            stmt = stmt.order_by(asc(sort_column))
        
        # Apply pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        
        # Execute query
        result = await session.execute(stmt)
        games = result.scalars().unique().all()
        
        return list(games), total
    
    @staticmethod
    async def search_games(
        session: AsyncSession,
        query: str,
        limit: int = 10,
    ) -> List[DimGame]:
        """
        Search games by name
        
        Args:
            session: Database session
            query: Search query
            limit: Max results
            
        Returns:
            List of matching games
        """
        stmt = (
            select(DimGame)
            .where(DimGame.name.ilike(f"%{query}%"))
            .limit(limit)
        )
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_game_avg_recent_players(
        session: AsyncSession,
        game_id: int,
        months: int = 3,
    ) -> Optional[int]:
        """
        Get average concurrent players for recent months
        
        Args:
            session: Database session
            game_id: Game ID
            months: Number of recent months
            
        Returns:
            Average player count or None
        """
        stmt = (
            select(func.avg(FactPlayerPrice.concurrent_players_avg))
            .where(FactPlayerPrice.game_id == game_id)
            .order_by(desc(FactPlayerPrice.date_id))
            .limit(months)
        )
        
        result = await session.execute(stmt)
        avg = result.scalar()
        
        return int(avg) if avg else None
