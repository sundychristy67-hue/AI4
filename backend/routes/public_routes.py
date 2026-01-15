from fastapi import APIRouter, HTTPException, status
from typing import List
from models import PublicGameResponse
from database import fetch_all, rows_to_list
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/public', tags=['Public'])


@router.get('/games', response_model=List[PublicGameResponse])
async def get_public_games():
    """
    Get list of games visible to the public (no auth required).
    Shows: name, description, download link, availability status.
    Hides: credentials-related info, internal flags.
    """
    games = await fetch_all(
        """
        SELECT id, name, description, tagline, thumbnail, icon_url, category, 
               download_url, platforms, availability_status, is_featured
        FROM games 
        WHERE is_active = TRUE 
        ORDER BY is_featured DESC, display_order ASC, created_at DESC
        """
    )
    
    result = []
    for g in rows_to_list(games):
        # Convert platforms array if needed
        platforms = g.get('platforms', ['android'])
        if isinstance(platforms, str):
            platforms = [platforms]
        g['platforms'] = platforms
        result.append(PublicGameResponse(**g))
    
    return result


@router.get('/games/{game_id}', response_model=PublicGameResponse)
async def get_public_game(game_id: str):
    """Get a single game's public info."""
    from database import fetch_one, row_to_dict
    
    game = await fetch_one(
        """
        SELECT id, name, description, tagline, thumbnail, icon_url, category, 
               download_url, platforms, availability_status, is_featured
        FROM games 
        WHERE id = $1 AND is_active = TRUE
        """,
        game_id
    )
    
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Game not found')
    
    game = row_to_dict(game)
    platforms = game.get('platforms', ['android'])
    if isinstance(platforms, str):
        platforms = [platforms]
    game['platforms'] = platforms
    
    return PublicGameResponse(**game)


@router.get('/status')
async def get_platform_status():
    """Get platform status (no auth required)."""
    from database import fetch_one
    
    # Get counts
    total_games = (await fetch_one("SELECT COUNT(*) as count FROM games WHERE is_active = TRUE"))['count']
    available_games = (await fetch_one(
        "SELECT COUNT(*) as count FROM games WHERE is_active = TRUE AND availability_status = 'available'"
    ))['count']
    
    return {
        'status': 'online',
        'total_games': total_games,
        'available_games': available_games,
        'message': 'Platform is operational'
    }
