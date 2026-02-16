"""
Database ORM Models
SQLAlchemy models matching the Star Schema
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DECIMAL, 
    ForeignKey, UniqueConstraint, Index, Enum, Text, TIMESTAMP
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
import enum

from app.db.session import Base


class AnalysisTypeEnum(str, enum.Enum):
    """Analysis type enumeration"""
    DID = "did"
    KAPLAN_MEIER = "kaplan_meier"
    COX_PH = "cox_ph"
    ELASTICITY = "elasticity"


# ========================================
# Dimension Tables
# ========================================

class DimDate(Base):
    """Calendar dimension table"""
    __tablename__ = "dim_date"
    
    date_id = Column(Integer, primary_key=True, autoincrement=True)
    full_date = Column(Date, unique=True, nullable=False)
    year = Column(Integer, nullable=False)
    quarter = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    day = Column(Integer, nullable=False)
    day_of_week = Column(Integer, nullable=False)
    is_weekend = Column(Boolean, nullable=False)
    is_steam_sale_period = Column(Boolean, default=False)
    steam_sale_name = Column(String(100))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    # Relationships
    facts = relationship("FactPlayerPrice", back_populates="date")


class DimGenre(Base):
    """Game genre dimension table"""
    __tablename__ = "dim_genre"
    
    genre_id = Column(Integer, primary_key=True, autoincrement=True)
    genre_name = Column(String(100), unique=True, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    # Relationships
    facts = relationship("FactPlayerPrice", back_populates="genre")
    analysis_results = relationship("AnalysisResult", back_populates="genre")


class DimTag(Base):
    """Game tag dimension table"""
    __tablename__ = "dim_tag"
    
    tag_id = Column(Integer, primary_key=True, autoincrement=True)
    tag_name = Column(String(100), unique=True, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    # Relationships
    games = relationship("BridgeGameTag", back_populates="tag")


class DimGame(Base):
    """Game dimension table"""
    __tablename__ = "dim_game"
    
    game_id = Column(Integer, primary_key=True, autoincrement=True)
    appid = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(500), nullable=False)
    developer = Column(String(500))
    publisher = Column(String(500))
    release_date = Column(Date)
    is_free = Column(Boolean, default=False)
    steamspy_owners_min = Column(Integer)
    steamspy_owners_max = Column(Integer)
    positive_reviews = Column(Integer, default=0)
    negative_reviews = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    facts = relationship("FactPlayerPrice", back_populates="game")
    tags = relationship("BridgeGameTag", back_populates="game")
    analysis_results = relationship("AnalysisResult", back_populates="game")


class BridgeGameTag(Base):
    """Bridge table for game-tag many-to-many relationship"""
    __tablename__ = "bridge_game_tag"
    
    game_id = Column(Integer, ForeignKey("dim_game.game_id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("dim_tag.tag_id", ondelete="CASCADE"), primary_key=True)
    
    # Relationships
    game = relationship("DimGame", back_populates="tags")
    tag = relationship("DimTag", back_populates="games")


# ========================================
# Fact Table
# ========================================

class FactPlayerPrice(Base):
    """Fact table for player counts and pricing data"""
    __tablename__ = "fact_player_price"
    
    fact_id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey("dim_game.game_id", ondelete="CASCADE"), nullable=False)
    date_id = Column(Integer, ForeignKey("dim_date.date_id"), nullable=False)
    genre_id = Column(Integer, ForeignKey("dim_genre.genre_id"))
    
    # Player metrics
    concurrent_players_avg = Column(Integer)
    concurrent_players_peak = Column(Integer)
    gain_pct = Column(DECIMAL(10, 2))
    avg_players_month = Column(Integer)
    peak_players_month = Column(Integer)
    
    # Pricing metrics
    current_price = Column(DECIMAL(10, 2))
    original_price = Column(DECIMAL(10, 2))
    discount_pct = Column(DECIMAL(5, 2), default=0)
    is_discount_active = Column(Boolean, default=False)
    
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    
    # Unique constraint
    __table_args__ = (
        UniqueConstraint('game_id', 'date_id', name='uq_game_date'),
        Index('idx_fact_player_price_game', 'game_id'),
        Index('idx_fact_player_price_date', 'date_id'),
        Index('idx_fact_player_price_genre', 'genre_id'),
    )
    
    # Relationships
    game = relationship("DimGame", back_populates="facts")
    date = relationship("DimDate", back_populates="facts")
    genre = relationship("DimGenre", back_populates="facts")


# ========================================
# Analysis Results Table
# ========================================

class AnalysisResult(Base):
    """Table for storing analytical model outputs"""
    __tablename__ = "analysis_results"
    
    result_id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_type = Column(Enum(AnalysisTypeEnum), nullable=False)
    game_id = Column(Integer, ForeignKey("dim_game.game_id"))
    genre_id = Column(Integer, ForeignKey("dim_genre.genre_id"))
    parameters = Column(JSONB, nullable=False)
    results = Column(JSONB, nullable=False)
    executed_at = Column(TIMESTAMP, default=datetime.utcnow)
    model_version = Column(String(50), default="1.0.0")
    
    # Indexes
    __table_args__ = (
        Index('idx_analysis_results_type', 'analysis_type'),
        Index('idx_analysis_results_game', 'game_id'),
        Index('idx_analysis_results_executed', 'executed_at'),
    )
    
    # Relationships
    game = relationship("DimGame", back_populates="analysis_results")
    genre = relationship("DimGenre", back_populates="analysis_results")
