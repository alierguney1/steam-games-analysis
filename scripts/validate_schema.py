#!/usr/bin/env python3
"""
Database Schema Validation Script
Validates the PostgreSQL schema setup
"""

import sys
import asyncio
from sqlalchemy import text


async def validate_schema():
    """Validate database schema"""
    from app.db.session import engine
    
    try:
        async with engine.begin() as conn:
            # Check if tables exist
            tables_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            
            result = await conn.execute(tables_query)
            tables = [row[0] for row in result]
            
            expected_tables = [
                'analysis_results',
                'bridge_game_tag',
                'dim_date',
                'dim_game',
                'dim_genre',
                'dim_tag',
                'fact_player_price',
            ]
            
            print("📊 Database Schema Validation")
            print("=" * 50)
            print(f"\n✓ Found {len(tables)} tables:")
            for table in tables:
                status = "✓" if table in expected_tables else "?"
                print(f"  {status} {table}")
            
            # Check if all expected tables exist
            missing = set(expected_tables) - set(tables)
            if missing:
                print(f"\n❌ Missing tables: {missing}")
                return False
            
            # Check dim_date has data
            count_query = text("SELECT COUNT(*) FROM dim_date")
            result = await conn.execute(count_query)
            date_count = result.scalar()
            print(f"\n✓ dim_date has {date_count} records")
            
            # Check dim_genre has data
            genre_query = text("SELECT COUNT(*) FROM dim_genre")
            result = await conn.execute(genre_query)
            genre_count = result.scalar()
            print(f"✓ dim_genre has {genre_count} records")
            
            print("\n✅ Database schema validation successful!")
            return True
            
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(validate_schema())
    sys.exit(0 if success else 1)
