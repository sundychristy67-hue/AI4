"""
Public Routes - No Authentication Required
Accessible by anyone for sharing and browsing
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from models import PublicGameResponse, GameAvailability
from database import get_database
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/public', tags=['Public'])


@router.get('/games', response_model=List[PublicGameResponse])
async def get_public_games(
    search: Optional[str] = Query(None, description="Search by game name"),
    category: Optional[str] = Query(None, description="Filter by category"),
    availability: Optional[str] = Query(None, description="Filter by availability: available, maintenance, unavailable"),
    featured_only: bool = Query(False, description="Show only featured games"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Get list of public games - no authentication required.
    Safe for sharing in Messenger, WhatsApp, etc.
    """
    db = await get_database()
    
    # Build query - only active games
    query = {'is_active': True}
    
    # Search filter
    if search:
        query['name'] = {'$regex': search, '$options': 'i'}
    
    # Category filter
    if category:
        query['category'] = category
    
    # Availability filter
    if availability:
        query['availability_status'] = availability
    
    # Featured filter
    if featured_only:
        query['is_featured'] = True
    
    # Fetch games sorted by display_order, then by name
    games = await db.games.find(
        query,
        {'_id': 0}
    ).sort([('display_order', 1), ('name', 1)]).skip(offset).limit(limit).to_list(limit)
    
    # Transform to public response (exclude sensitive fields)
    public_games = []
    for game in games:
        public_games.append(PublicGameResponse(
            id=game['id'],
            name=game['name'],
            description=game.get('description', ''),
            tagline=game.get('tagline'),
            thumbnail=game.get('thumbnail'),
            icon_url=game.get('icon_url'),
            category=game.get('category'),
            download_url=game.get('download_url'),
            platforms=game.get('platforms', ['android']),
            availability_status=game.get('availability_status', 'available'),
            is_featured=game.get('is_featured', False)
        ))
    
    return public_games


@router.get('/games/{game_id}', response_model=PublicGameResponse)
async def get_public_game_detail(game_id: str):
    """Get single game details - no authentication required."""
    db = await get_database()
    
    game = await db.games.find_one(
        {'id': game_id, 'is_active': True},
        {'_id': 0}
    )
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    return PublicGameResponse(
        id=game['id'],
        name=game['name'],
        description=game.get('description', ''),
        tagline=game.get('tagline'),
        thumbnail=game.get('thumbnail'),
        icon_url=game.get('icon_url'),
        category=game.get('category'),
        download_url=game.get('download_url'),
        platforms=game.get('platforms', ['android']),
        availability_status=game.get('availability_status', 'available'),
        is_featured=game.get('is_featured', False)
    )


@router.get('/games/categories/list')
async def get_game_categories():
    """Get list of game categories."""
    db = await get_database()
    
    # Get distinct categories from active games
    categories = await db.games.distinct('category', {'is_active': True, 'category': {'$ne': None}})
    
    return {'categories': [c for c in categories if c]}


@router.get('/games/stats/count')
async def get_games_count(
    availability: Optional[str] = Query(None)
):
    """Get count of games - useful for pagination."""
    db = await get_database()
    
    query = {'is_active': True}
    if availability:
        query['availability_status'] = availability
    
    count = await db.games.count_documents(query)
    
    return {'total': count}


@router.get('/site-info')
async def get_site_info():
    """Get public site information for footer/contact."""
    # This can be expanded to fetch from settings
    return {
        'name': 'VaultLink',
        'tagline': 'Your trusted gaming platform',
        'contact': {
            'facebook': 'https://facebook.com/yourpage',
            'messenger': 'https://m.me/yourpage',
            'telegram': None,
            'whatsapp': None
        },
        'support_text': 'Need help? Chat with us on Facebook!'
    }
