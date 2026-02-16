"""
Games API Endpoints
CRUD operations for games
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.db.repositories.game_repo import GameRepository
from app.schemas.game import (
    GameCreate,
    GameUpdate,
    GameResponse,
    GameDetailResponse,
    GameListResponse,
    GameListItem,
)

router = APIRouter()


@router.post(
    "/",
    response_model=GameResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new game",
)
async def create_game(
    game_data: GameCreate,
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new game in the database.
    
    - **appid**: Steam App ID (unique)
    - **name**: Game name
    - **developer**: Developer name (optional)
    - **publisher**: Publisher name (optional)
    - **release_date**: Release date (optional)
    - **is_free**: Whether the game is free to play
    """
    # Check if game with this appid already exists
    existing_game = await GameRepository.get_game_by_appid(session, game_data.appid)
    if existing_game:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Game with appid {game_data.appid} already exists",
        )
    
    game = await GameRepository.create_game(session, game_data)
    return game


@router.get(
    "/",
    response_model=GameListResponse,
    summary="List games with filtering and pagination",
)
async def list_games(
    query: str = Query(None, description="Search query (name, developer, publisher)"),
    genre: str = Query(None, description="Filter by genre"),
    is_free: bool = Query(None, description="Filter by free/paid"),
    min_players: int = Query(None, ge=0, description="Minimum average players"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(30, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("name", description="Sort field"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order"),
    session: AsyncSession = Depends(get_session),
):
    """
    List games with optional filtering, sorting, and pagination.
    
    **Filters:**
    - `query`: Search in name, developer, or publisher
    - `genre`: Filter by genre name
    - `is_free`: Filter by free (true) or paid (false) games
    - `min_players`: Minimum average concurrent players (recent 3 months)
    
    **Sorting:**
    - `sort_by`: Field to sort by (name, release_date, etc.)
    - `sort_order`: Sort direction (asc, desc)
    
    **Pagination:**
    - `page`: Page number (starts at 1)
    - `page_size`: Number of items per page (max 100)
    """
    games, total = await GameRepository.list_games(
        session=session,
        query=query,
        genre=genre,
        is_free=is_free,
        min_players=min_players,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    
    # Calculate recent average players for each game
    game_items = []
    for game in games:
        avg_players = await GameRepository.get_game_avg_recent_players(
            session, game.game_id, months=3
        )
        
        game_items.append(
            GameListItem(
                game_id=game.game_id,
                appid=game.appid,
                name=game.name,
                developer=game.developer,
                release_date=game.release_date,
                is_free=game.is_free,
                avg_recent_players=avg_players,
                current_price=None,  # TODO: Get from latest fact
            )
        )
    
    total_pages = (total + page_size - 1) // page_size
    
    return GameListResponse(
        games=game_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/search",
    response_model=List[GameResponse],
    summary="Search games by name",
)
async def search_games(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    session: AsyncSession = Depends(get_session),
):
    """
    Quick search for games by name.
    
    Returns up to `limit` games matching the search query.
    """
    games = await GameRepository.search_games(session, query=q, limit=limit)
    return games


@router.get(
    "/{game_id}",
    response_model=GameDetailResponse,
    summary="Get game details",
)
async def get_game(
    game_id: int,
    session: AsyncSession = Depends(get_session),
):
    """
    Get detailed information about a specific game.
    
    Includes:
    - Basic game information
    - Tags
    - Recent player/price data (last 12 months)
    """
    game = await GameRepository.get_game_by_id(
        session,
        game_id,
        include_tags=True,
        include_recent_facts=True,
    )
    
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game with id {game_id} not found",
        )
    
    return game


@router.get(
    "/appid/{appid}",
    response_model=GameResponse,
    summary="Get game by Steam App ID",
)
async def get_game_by_appid(
    appid: int,
    session: AsyncSession = Depends(get_session),
):
    """
    Get game information by Steam App ID.
    """
    game = await GameRepository.get_game_by_appid(session, appid)
    
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game with appid {appid} not found",
        )
    
    return game


@router.put(
    "/{game_id}",
    response_model=GameResponse,
    summary="Update game information",
)
async def update_game(
    game_id: int,
    game_data: GameUpdate,
    session: AsyncSession = Depends(get_session),
):
    """
    Update game information.
    
    Only provided fields will be updated.
    """
    game = await GameRepository.update_game(session, game_id, game_data)
    
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game with id {game_id} not found",
        )
    
    return game


@router.delete(
    "/{game_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a game",
)
async def delete_game(
    game_id: int,
    session: AsyncSession = Depends(get_session),
):
    """
    Delete a game from the database.
    
    This will also delete all associated facts and relationships.
    """
    deleted = await GameRepository.delete_game(session, game_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game with id {game_id} not found",
        )
    
    return None
