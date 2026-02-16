"""
Analysis Results Repository
CRUD operations for storing and retrieving analysis results
"""

from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
import json

from app.db.models import AnalysisResult, AnalysisTypeEnum


class AnalysisRepository:
    """Repository for analysis results"""
    
    @staticmethod
    async def create_result(
        session: AsyncSession,
        analysis_type: AnalysisTypeEnum,
        parameters: Dict,
        results: Dict,
        game_id: Optional[int] = None,
        genre_id: Optional[int] = None,
        model_version: str = "1.0.0",
    ) -> AnalysisResult:
        """
        Store analysis result in database
        
        Args:
            session: Database session
            analysis_type: Type of analysis (did, kaplan_meier, cox_ph, elasticity)
            parameters: Analysis parameters (stored as JSONB)
            results: Analysis results (stored as JSONB)
            game_id: Optional game_id if analysis is game-specific
            genre_id: Optional genre_id if analysis is genre-specific
            model_version: Model version string
        
        Returns:
            Created AnalysisResult instance
        """
        analysis_result = AnalysisResult(
            analysis_type=analysis_type,
            game_id=game_id,
            genre_id=genre_id,
            parameters=parameters,
            results=results,
            model_version=model_version,
            executed_at=datetime.utcnow(),
        )
        
        session.add(analysis_result)
        await session.commit()
        await session.refresh(analysis_result)
        
        return analysis_result
    
    @staticmethod
    async def get_result_by_id(
        session: AsyncSession,
        result_id: int,
    ) -> Optional[AnalysisResult]:
        """
        Get analysis result by ID
        
        Args:
            session: Database session
            result_id: Result ID
        
        Returns:
            AnalysisResult or None
        """
        result = await session.execute(
            select(AnalysisResult).where(AnalysisResult.result_id == result_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_latest_results(
        session: AsyncSession,
        analysis_type: Optional[AnalysisTypeEnum] = None,
        game_id: Optional[int] = None,
        genre_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[AnalysisResult]:
        """
        Get latest analysis results with optional filters
        
        Args:
            session: Database session
            analysis_type: Optional analysis type filter
            game_id: Optional game_id filter
            genre_id: Optional genre_id filter
            limit: Maximum number of results
        
        Returns:
            List of AnalysisResult instances
        """
        query = select(AnalysisResult)
        
        filters = []
        if analysis_type:
            filters.append(AnalysisResult.analysis_type == analysis_type)
        if game_id:
            filters.append(AnalysisResult.game_id == game_id)
        if genre_id:
            filters.append(AnalysisResult.genre_id == genre_id)
        
        if filters:
            query = query.where(and_(*filters))
        
        query = query.order_by(desc(AnalysisResult.executed_at)).limit(limit)
        
        result = await session.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_did_results(
        session: AsyncSession,
        game_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[AnalysisResult]:
        """
        Get Difference-in-Differences analysis results
        
        Args:
            session: Database session
            game_id: Optional game_id filter
            limit: Maximum number of results
        
        Returns:
            List of DiD results
        """
        return await AnalysisRepository.get_latest_results(
            session,
            analysis_type=AnalysisTypeEnum.DID,
            game_id=game_id,
            limit=limit,
        )
    
    @staticmethod
    async def get_survival_results(
        session: AsyncSession,
        analysis_type: AnalysisTypeEnum = AnalysisTypeEnum.KAPLAN_MEIER,
        genre_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[AnalysisResult]:
        """
        Get survival analysis results (Kaplan-Meier or Cox PH)
        
        Args:
            session: Database session
            analysis_type: KAPLAN_MEIER or COX_PH
            genre_id: Optional genre_id filter
            limit: Maximum number of results
        
        Returns:
            List of survival analysis results
        """
        if analysis_type not in [AnalysisTypeEnum.KAPLAN_MEIER, AnalysisTypeEnum.COX_PH]:
            raise ValueError(f"Invalid survival analysis type: {analysis_type}")
        
        return await AnalysisRepository.get_latest_results(
            session,
            analysis_type=analysis_type,
            genre_id=genre_id,
            limit=limit,
        )
    
    @staticmethod
    async def get_elasticity_results(
        session: AsyncSession,
        genre_id: Optional[int] = None,
        limit: int = 10,
    ) -> List[AnalysisResult]:
        """
        Get price elasticity results
        
        Args:
            session: Database session
            genre_id: Optional genre_id filter
            limit: Maximum number of results
        
        Returns:
            List of elasticity results
        """
        return await AnalysisRepository.get_latest_results(
            session,
            analysis_type=AnalysisTypeEnum.ELASTICITY,
            genre_id=genre_id,
            limit=limit,
        )
    
    @staticmethod
    async def delete_result(
        session: AsyncSession,
        result_id: int,
    ) -> bool:
        """
        Delete analysis result
        
        Args:
            session: Database session
            result_id: Result ID to delete
        
        Returns:
            True if deleted, False if not found
        """
        result = await AnalysisRepository.get_result_by_id(session, result_id)
        
        if result:
            await session.delete(result)
            await session.commit()
            return True
        
        return False
    
    @staticmethod
    async def get_results_summary(
        session: AsyncSession,
    ) -> Dict:
        """
        Get summary statistics of analysis results
        
        Args:
            session: Database session
        
        Returns:
            Dictionary with summary statistics
        """
        from sqlalchemy import func
        
        # Count by analysis type
        type_counts = await session.execute(
            select(
                AnalysisResult.analysis_type,
                func.count(AnalysisResult.result_id).label("count"),
            ).group_by(AnalysisResult.analysis_type)
        )
        
        type_count_dict = {
            row.analysis_type.value: row.count for row in type_counts.all()
        }
        
        # Total count
        total_result = await session.execute(
            select(func.count(AnalysisResult.result_id))
        )
        total_count = total_result.scalar()
        
        # Latest execution time
        latest_result = await session.execute(
            select(func.max(AnalysisResult.executed_at))
        )
        latest_execution = latest_result.scalar()
        
        return {
            "total_analyses": total_count,
            "by_type": type_count_dict,
            "latest_execution": latest_execution.isoformat() if latest_execution else None,
        }
