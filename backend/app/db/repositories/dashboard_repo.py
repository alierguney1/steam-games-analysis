"""
Dashboard Repository
Query operations for dashboard metrics and summaries
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import aliased

from app.db.models import (
    DimGame,
    FactPlayerPrice,
    DimGenre,
    DimDate,
    AnalysisResult,
    AnalysisTypeEnum,
)


class DashboardRepository:
    """Repository for dashboard queries"""
    
    @staticmethod
    async def get_summary_metrics(session: AsyncSession) -> Dict[str, Any]:
        """
        Get summary metrics for dashboard
        
        Args:
            session: Database session
            
        Returns:
            Dictionary with summary metrics
        """
        # Total games
        total_games_query = select(func.count()).select_from(DimGame)
        total_games_result = await session.execute(total_games_query)
        total_games = total_games_result.scalar() or 0
        
        # Total facts
        total_facts_query = select(func.count()).select_from(FactPlayerPrice)
        total_facts_result = await session.execute(total_facts_query)
        total_facts = total_facts_result.scalar() or 0
        
        # Average concurrent players (recent month)
        avg_players_query = (
            select(func.avg(FactPlayerPrice.concurrent_players_avg))
            .join(DimDate)
            .where(DimDate.full_date >= datetime.utcnow() - timedelta(days=30))
        )
        avg_players_result = await session.execute(avg_players_query)
        avg_concurrent_players = int(avg_players_result.scalar() or 0)
        
        # Active discounts
        active_discount_query = (
            select(func.count())
            .select_from(FactPlayerPrice)
            .where(FactPlayerPrice.is_discount_active == True)
            .join(DimDate)
            .where(DimDate.full_date >= datetime.utcnow() - timedelta(days=7))
        )
        active_discount_result = await session.execute(active_discount_query)
        active_discount_count = active_discount_result.scalar() or 0
        
        # Average discount percentage
        avg_discount_query = (
            select(func.avg(FactPlayerPrice.discount_pct))
            .where(FactPlayerPrice.is_discount_active == True)
            .join(DimDate)
            .where(DimDate.full_date >= datetime.utcnow() - timedelta(days=7))
        )
        avg_discount_result = await session.execute(avg_discount_query)
        avg_discount_pct = float(avg_discount_result.scalar() or 0)
        
        # Latest data date
        latest_date_query = select(func.max(DimDate.full_date)).select_from(DimDate)
        latest_date_result = await session.execute(latest_date_query)
        latest_data_date = latest_date_result.scalar()
        
        return {
            "total_games": total_games,
            "total_facts": total_facts,
            "avg_concurrent_players": avg_concurrent_players,
            "active_discount_count": active_discount_count,
            "avg_discount_pct": avg_discount_pct,
            "latest_data_date": latest_data_date,
        }
    
    @staticmethod
    async def get_top_games_by_players(
        session: AsyncSession,
        limit: int = 10,
    ) -> List[Tuple[DimGame, float]]:
        """
        Get top games by average concurrent players (recent 3 months)
        
        Args:
            session: Database session
            limit: Number of games to return
            
        Returns:
            List of (game, avg_players) tuples
        """
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        query = (
            select(
                DimGame,
                func.avg(FactPlayerPrice.concurrent_players_avg).label("avg_players")
            )
            .join(FactPlayerPrice, DimGame.game_id == FactPlayerPrice.game_id)
            .join(DimDate, FactPlayerPrice.date_id == DimDate.date_id)
            .where(DimDate.full_date >= cutoff_date)
            .where(FactPlayerPrice.concurrent_players_avg.isnot(None))
            .group_by(DimGame.game_id)
            .order_by(desc("avg_players"))
            .limit(limit)
        )
        
        result = await session.execute(query)
        return [(row[0], float(row[1] or 0)) for row in result.all()]
    
    @staticmethod
    async def get_top_games_by_growth(
        session: AsyncSession,
        limit: int = 10,
    ) -> List[Tuple[DimGame, float]]:
        """
        Get top games by player growth rate
        
        Args:
            session: Database session
            limit: Number of games to return
            
        Returns:
            List of (game, growth_pct) tuples
        """
        # Get games with at least 2 months of data
        # Calculate growth as (recent_avg - old_avg) / old_avg
        
        recent_cutoff = datetime.utcnow() - timedelta(days=30)
        old_cutoff = datetime.utcnow() - timedelta(days=90)
        old_start = datetime.utcnow() - timedelta(days=120)
        
        # Subquery for recent average
        recent_avg = (
            select(
                FactPlayerPrice.game_id,
                func.avg(FactPlayerPrice.concurrent_players_avg).label("recent_avg")
            )
            .join(DimDate)
            .where(DimDate.full_date >= recent_cutoff)
            .where(FactPlayerPrice.concurrent_players_avg.isnot(None))
            .group_by(FactPlayerPrice.game_id)
        ).subquery()
        
        # Subquery for old average
        old_avg = (
            select(
                FactPlayerPrice.game_id,
                func.avg(FactPlayerPrice.concurrent_players_avg).label("old_avg")
            )
            .join(DimDate)
            .where(and_(
                DimDate.full_date >= old_start,
                DimDate.full_date < old_cutoff
            ))
            .where(FactPlayerPrice.concurrent_players_avg.isnot(None))
            .group_by(FactPlayerPrice.game_id)
        ).subquery()
        
        # Main query
        growth_expr = (
            (recent_avg.c.recent_avg - old_avg.c.old_avg) / old_avg.c.old_avg * 100
        ).label("growth_pct")
        
        query = (
            select(DimGame, growth_expr)
            .join(recent_avg, DimGame.game_id == recent_avg.c.game_id)
            .join(old_avg, DimGame.game_id == old_avg.c.game_id)
            .where(old_avg.c.old_avg > 0)
            .order_by(desc("growth_pct"))
            .limit(limit)
        )
        
        result = await session.execute(query)
        return [(row[0], float(row[1] or 0)) for row in result.all()]
    
    @staticmethod
    async def get_top_discounted_games(
        session: AsyncSession,
        limit: int = 10,
    ) -> List[Tuple[DimGame, float]]:
        """
        Get top discounted games
        
        Args:
            session: Database session
            limit: Number of games to return
            
        Returns:
            List of (game, discount_pct) tuples
        """
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        query = (
            select(
                DimGame,
                func.max(FactPlayerPrice.discount_pct).label("max_discount")
            )
            .join(FactPlayerPrice)
            .join(DimDate)
            .where(DimDate.full_date >= cutoff_date)
            .where(FactPlayerPrice.is_discount_active == True)
            .where(FactPlayerPrice.discount_pct.isnot(None))
            .group_by(DimGame.game_id)
            .order_by(desc("max_discount"))
            .limit(limit)
        )
        
        result = await session.execute(query)
        return [(row[0], float(row[1] or 0)) for row in result.all()]
    
    @staticmethod
    async def get_genre_distribution(
        session: AsyncSession,
    ) -> List[Dict[str, Any]]:
        """
        Get genre distribution with game counts and metrics
        
        Args:
            session: Database session
            
        Returns:
            List of genre distribution dictionaries
        """
        query = (
            select(
                DimGenre.genre_name,
                func.count(func.distinct(FactPlayerPrice.game_id)).label("game_count"),
                func.avg(FactPlayerPrice.concurrent_players_avg).label("avg_players"),
                func.avg(FactPlayerPrice.current_price).label("avg_price"),
                func.sum(FactPlayerPrice.concurrent_players_avg).label("total_players"),
            )
            .join(FactPlayerPrice, DimGenre.genre_id == FactPlayerPrice.genre_id)
            .group_by(DimGenre.genre_name)
            .order_by(desc("game_count"))
        )
        
        result = await session.execute(query)
        
        distributions = []
        for row in result.all():
            distributions.append({
                "genre_name": row[0],
                "game_count": row[1] or 0,
                "avg_players": int(row[2] or 0),
                "avg_price": float(row[3] or 0),
                "total_players": int(row[4] or 0),
            })
        
        return distributions
    
    @staticmethod
    async def get_analysis_summary(
        session: AsyncSession,
    ) -> List[Dict[str, Any]]:
        """
        Get summary of analyses by type
        
        Args:
            session: Database session
            
        Returns:
            List of analysis summary dictionaries
        """
        query = (
            select(
                AnalysisResult.analysis_type,
                func.count().label("count"),
                func.max(AnalysisResult.executed_at).label("last_executed"),
            )
            .group_by(AnalysisResult.analysis_type)
        )
        
        result = await session.execute(query)
        
        summaries = []
        for row in result.all():
            summaries.append({
                "analysis_type": row[0],
                "count": row[1] or 0,
                "last_executed": row[2],
            })
        
        return summaries
    
    @staticmethod
    async def get_time_series_players(
        session: AsyncSession,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        game_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get time series data for player counts
        
        Args:
            session: Database session
            start_date: Start date filter
            end_date: End date filter
            game_id: Optional game ID filter
            
        Returns:
            List of time series points
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=365)
        if not end_date:
            end_date = datetime.utcnow()
        
        query = (
            select(
                DimDate.full_date,
                func.avg(FactPlayerPrice.concurrent_players_avg).label("avg_players")
            )
            .join(FactPlayerPrice.date)
            .where(and_(
                DimDate.full_date >= start_date,
                DimDate.full_date <= end_date
            ))
            .where(FactPlayerPrice.concurrent_players_avg.isnot(None))
        )
        
        if game_id:
            query = query.where(FactPlayerPrice.game_id == game_id)
        
        query = query.group_by(DimDate.full_date).order_by(DimDate.full_date)
        
        result = await session.execute(query)
        
        return [
            {"date": row[0], "value": float(row[1] or 0)}
            for row in result.all()
        ]
