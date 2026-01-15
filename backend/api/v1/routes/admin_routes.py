"""
API v1 Admin Routes - Referral Perk Management
"""
from fastapi import APIRouter, Request, Header, HTTPException, status
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid
import json

from ..core.database import fetch_one, fetch_all, execute
from ..core.config import ErrorCodes
from .dependencies import authenticate_request

router = APIRouter(prefix="/admin", tags=["Admin"])


# ==================== MODELS ====================

class PerkCreate(BaseModel):
    """Create a new referral perk"""
    referral_code: str = Field(..., min_length=4, max_length=20)
    game_name: Optional[str] = Field(None, description="Specific game or null for all games")
    percent_bonus: float = Field(0.0, ge=0, le=100)
    flat_bonus: float = Field(0.0, ge=0)
    max_bonus: Optional[float] = Field(None, ge=0)
    min_amount: Optional[float] = Field(None, ge=0)
    valid_until: Optional[datetime] = None
    max_uses: Optional[int] = Field(None, ge=1)
    is_active: bool = True


class PerkUpdate(BaseModel):
    """Update an existing perk"""
    percent_bonus: Optional[float] = Field(None, ge=0, le=100)
    flat_bonus: Optional[float] = Field(None, ge=0)
    max_bonus: Optional[float] = None
    min_amount: Optional[float] = None
    valid_until: Optional[datetime] = None
    max_uses: Optional[int] = None
    is_active: Optional[bool] = None


class PerkResponse(BaseModel):
    """Perk response"""
    perk_id: str
    referral_code: str
    game_name: Optional[str]
    percent_bonus: float
    flat_bonus: float
    max_bonus: Optional[float]
    min_amount: Optional[float]
    valid_from: Optional[datetime]
    valid_until: Optional[datetime]
    max_uses: Optional[int]
    current_uses: int
    is_active: bool
    created_at: datetime


class GameBonusRuleUpdate(BaseModel):
    """Update game bonus rules"""
    game_name: str
    bonus_rules: dict


# ==================== PERK ENDPOINTS ====================

@router.get(
    "/perks",
    response_model=List[PerkResponse],
    summary="List all referral perks",
    description="Get all referral perks. Admin access required."
)
async def list_perks(
    request: Request,
    referral_code: Optional[str] = None,
    is_active: Optional[bool] = None,
    authorization: str = Header(..., alias="Authorization")
):
    """List all referral perks"""
    auth = await authenticate_request(request, None, None, authorization)
    
    query = "SELECT * FROM api_referral_perks WHERE 1=1"
    params = []
    
    if referral_code:
        params.append(referral_code.upper())
        query += f" AND referral_code = ${len(params)}"
    
    if is_active is not None:
        params.append(is_active)
        query += f" AND is_active = ${len(params)}"
    
    query += " ORDER BY created_at DESC"
    
    perks = await fetch_all(query, *params) if params else await fetch_all(query)
    
    return [PerkResponse(
        perk_id=p['perk_id'],
        referral_code=p['referral_code'],
        game_name=p.get('game_name'),
        percent_bonus=p['percent_bonus'],
        flat_bonus=p['flat_bonus'],
        max_bonus=p.get('max_bonus'),
        min_amount=p.get('min_amount'),
        valid_from=p.get('valid_from'),
        valid_until=p.get('valid_until'),
        max_uses=p.get('max_uses'),
        current_uses=p.get('current_uses', 0),
        is_active=p['is_active'],
        created_at=p['created_at']
    ) for p in perks]


@router.post(
    "/perks",
    response_model=PerkResponse,
    summary="Create a referral perk",
    description="Create a new referral perk for a specific referral code."
)
async def create_perk(
    request: Request,
    data: PerkCreate,
    authorization: str = Header(..., alias="Authorization")
):
    """Create a new referral perk"""
    auth = await authenticate_request(request, None, None, authorization)
    
    # Verify referral code exists
    user = await fetch_one(
        "SELECT user_id FROM api_users WHERE referral_code = $1",
        data.referral_code.upper()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Referral code not found", "error_code": ErrorCodes.INVALID_REFERRAL_CODE}
        )
    
    # Verify game exists if specified
    if data.game_name:
        game = await fetch_one(
            "SELECT game_id FROM api_games WHERE game_name = $1",
            data.game_name.lower()
        )
        if not game:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Game not found", "error_code": ErrorCodes.GAME_NOT_FOUND}
            )
    
    perk_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    await execute('''
        INSERT INTO api_referral_perks (
            perk_id, referral_code, game_name, percent_bonus, flat_bonus,
            max_bonus, min_amount, valid_from, valid_until, max_uses, is_active, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
    ''', perk_id, data.referral_code.upper(), data.game_name.lower() if data.game_name else None,
        data.percent_bonus, data.flat_bonus, data.max_bonus, data.min_amount,
        now, data.valid_until, data.max_uses, data.is_active, now)
    
    return PerkResponse(
        perk_id=perk_id,
        referral_code=data.referral_code.upper(),
        game_name=data.game_name.lower() if data.game_name else None,
        percent_bonus=data.percent_bonus,
        flat_bonus=data.flat_bonus,
        max_bonus=data.max_bonus,
        min_amount=data.min_amount,
        valid_from=now,
        valid_until=data.valid_until,
        max_uses=data.max_uses,
        current_uses=0,
        is_active=data.is_active,
        created_at=now
    )


@router.get(
    "/perks/{perk_id}",
    response_model=PerkResponse,
    summary="Get a specific perk"
)
async def get_perk(
    request: Request,
    perk_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Get a specific perk by ID"""
    auth = await authenticate_request(request, None, None, authorization)
    
    perk = await fetch_one("SELECT * FROM api_referral_perks WHERE perk_id = $1", perk_id)
    
    if not perk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Perk not found"}
        )
    
    return PerkResponse(
        perk_id=perk['perk_id'],
        referral_code=perk['referral_code'],
        game_name=perk.get('game_name'),
        percent_bonus=perk['percent_bonus'],
        flat_bonus=perk['flat_bonus'],
        max_bonus=perk.get('max_bonus'),
        min_amount=perk.get('min_amount'),
        valid_from=perk.get('valid_from'),
        valid_until=perk.get('valid_until'),
        max_uses=perk.get('max_uses'),
        current_uses=perk.get('current_uses', 0),
        is_active=perk['is_active'],
        created_at=perk['created_at']
    )


@router.put(
    "/perks/{perk_id}",
    response_model=PerkResponse,
    summary="Update a perk"
)
async def update_perk(
    request: Request,
    perk_id: str,
    data: PerkUpdate,
    authorization: str = Header(..., alias="Authorization")
):
    """Update an existing perk"""
    auth = await authenticate_request(request, None, None, authorization)
    
    perk = await fetch_one("SELECT * FROM api_referral_perks WHERE perk_id = $1", perk_id)
    if not perk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Perk not found"}
        )
    
    updates = []
    params = []
    
    if data.percent_bonus is not None:
        params.append(data.percent_bonus)
        updates.append(f"percent_bonus = ${len(params)}")
    if data.flat_bonus is not None:
        params.append(data.flat_bonus)
        updates.append(f"flat_bonus = ${len(params)}")
    if data.max_bonus is not None:
        params.append(data.max_bonus if data.max_bonus > 0 else None)
        updates.append(f"max_bonus = ${len(params)}")
    if data.min_amount is not None:
        params.append(data.min_amount if data.min_amount > 0 else None)
        updates.append(f"min_amount = ${len(params)}")
    if data.valid_until is not None:
        params.append(data.valid_until)
        updates.append(f"valid_until = ${len(params)}")
    if data.max_uses is not None:
        params.append(data.max_uses if data.max_uses > 0 else None)
        updates.append(f"max_uses = ${len(params)}")
    if data.is_active is not None:
        params.append(data.is_active)
        updates.append(f"is_active = ${len(params)}")
    
    if updates:
        params.append(perk_id)
        await execute(
            f"UPDATE api_referral_perks SET {', '.join(updates)} WHERE perk_id = ${len(params)}",
            *params
        )
    
    # Fetch updated perk
    perk = await fetch_one("SELECT * FROM api_referral_perks WHERE perk_id = $1", perk_id)
    
    return PerkResponse(
        perk_id=perk['perk_id'],
        referral_code=perk['referral_code'],
        game_name=perk.get('game_name'),
        percent_bonus=perk['percent_bonus'],
        flat_bonus=perk['flat_bonus'],
        max_bonus=perk.get('max_bonus'),
        min_amount=perk.get('min_amount'),
        valid_from=perk.get('valid_from'),
        valid_until=perk.get('valid_until'),
        max_uses=perk.get('max_uses'),
        current_uses=perk.get('current_uses', 0),
        is_active=perk['is_active'],
        created_at=perk['created_at']
    )


@router.delete(
    "/perks/{perk_id}",
    summary="Delete a perk"
)
async def delete_perk(
    request: Request,
    perk_id: str,
    authorization: str = Header(..., alias="Authorization")
):
    """Delete a perk (soft delete - sets is_active to false)"""
    auth = await authenticate_request(request, None, None, authorization)
    
    perk = await fetch_one("SELECT * FROM api_referral_perks WHERE perk_id = $1", perk_id)
    if not perk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Perk not found"}
        )
    
    await execute("UPDATE api_referral_perks SET is_active = FALSE WHERE perk_id = $1", perk_id)
    
    return {"success": True, "message": "Perk deleted"}


# ==================== USER LOOKUP ====================

@router.get(
    "/users",
    summary="List users with referral codes",
    description="Get users for referral code lookup"
)
async def list_users(
    request: Request,
    search: Optional[str] = None,
    limit: int = 50,
    authorization: str = Header(..., alias="Authorization")
):
    """List users for admin lookup"""
    auth = await authenticate_request(request, None, None, authorization)
    
    if search:
        users = await fetch_all('''
            SELECT user_id, username, display_name, referral_code, is_active, created_at
            FROM api_users 
            WHERE username ILIKE $1 OR referral_code ILIKE $1 OR display_name ILIKE $1
            ORDER BY created_at DESC
            LIMIT $2
        ''', f'%{search}%', limit)
    else:
        users = await fetch_all('''
            SELECT user_id, username, display_name, referral_code, is_active, created_at
            FROM api_users 
            ORDER BY created_at DESC
            LIMIT $1
        ''', limit)
    
    return [{
        "user_id": u['user_id'],
        "username": u['username'],
        "display_name": u['display_name'],
        "referral_code": u['referral_code'],
        "is_active": u['is_active'],
        "created_at": u['created_at'].isoformat() if u.get('created_at') else None
    } for u in users]


# ==================== GAME BONUS RULES ====================

@router.get(
    "/games",
    summary="List games with bonus rules"
)
async def list_games_admin(
    request: Request,
    authorization: str = Header(..., alias="Authorization")
):
    """List all games with their bonus rules"""
    auth = await authenticate_request(request, None, None, authorization)
    
    games = await fetch_all("SELECT * FROM api_games ORDER BY display_name")
    
    result = []
    for g in games:
        bonus_rules = g.get('bonus_rules', {})
        if isinstance(bonus_rules, str):
            bonus_rules = json.loads(bonus_rules)
        
        result.append({
            "game_id": g['game_id'],
            "game_name": g['game_name'],
            "display_name": g['display_name'],
            "description": g.get('description'),
            "min_recharge_amount": g['min_recharge_amount'],
            "max_recharge_amount": g['max_recharge_amount'],
            "bonus_rules": bonus_rules,
            "is_active": g['is_active']
        })
    
    return result


@router.put(
    "/games/{game_name}/bonus-rules",
    summary="Update game bonus rules"
)
async def update_game_bonus_rules(
    request: Request,
    game_name: str,
    data: dict,
    authorization: str = Header(..., alias="Authorization")
):
    """Update bonus rules for a game"""
    auth = await authenticate_request(request, None, None, authorization)
    
    game = await fetch_one(
        "SELECT * FROM api_games WHERE game_name = $1",
        game_name.lower()
    )
    
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Game not found"}
        )
    
    await execute(
        "UPDATE api_games SET bonus_rules = $1 WHERE game_name = $2",
        json.dumps(data), game_name.lower()
    )
    
    return {"success": True, "message": "Bonus rules updated", "bonus_rules": data}


# ==================== STATS ====================

@router.get(
    "/stats",
    summary="Get admin statistics"
)
async def get_admin_stats(
    request: Request,
    authorization: str = Header(..., alias="Authorization")
):
    """Get admin dashboard statistics"""
    auth = await authenticate_request(request, None, None, authorization)
    
    total_users = (await fetch_one("SELECT COUNT(*) as count FROM api_users"))['count']
    total_orders = (await fetch_one("SELECT COUNT(*) as count FROM api_orders"))['count']
    total_perks = (await fetch_one("SELECT COUNT(*) as count FROM api_referral_perks WHERE is_active = TRUE"))['count']
    
    total_order_amount = await fetch_one(
        "SELECT COALESCE(SUM(recharge_amount), 0) as total FROM api_orders"
    )
    total_bonus_amount = await fetch_one(
        "SELECT COALESCE(SUM(bonus_amount), 0) as total FROM api_orders"
    )
    
    recent_orders = await fetch_all('''
        SELECT * FROM api_orders ORDER BY created_at DESC LIMIT 10
    ''')
    
    return {
        "total_users": total_users,
        "total_orders": total_orders,
        "total_active_perks": total_perks,
        "total_order_amount": total_order_amount['total'],
        "total_bonus_distributed": total_bonus_amount['total'],
        "recent_orders": [{
            "order_id": o['order_id'],
            "username": o['username'],
            "game_name": o['game_name'],
            "recharge_amount": o['recharge_amount'],
            "bonus_amount": o['bonus_amount'],
            "status": o['status'],
            "created_at": o['created_at'].isoformat() if o.get('created_at') else None
        } for o in recent_orders]
    }
