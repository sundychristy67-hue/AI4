from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from models import (
    ClientResponse, ClientFinancialSummary, LedgerTransactionResponse,
    ClientCredentialResponse, TransactionType, TransactionStatus, WalletType,
    ApplyReferralRequest, ApplyReferralResponse, LoadToGameRequest, LoadToGameResponse,
    OrderStatus, WalletSummary, ReferralBonusInfo, VisibilityLevel,
    ClientPasswordSetup, ClientPasswordLogin, ClientPasswordLoginResponse
)
from auth import (
    get_portal_client, validate_portal_token, get_portal_client_flexible,
    authenticate_client_password, create_client_access_token, hash_password
)
from database import get_database
from utils import (
    mask_credential, apply_referral_code, get_current_utc_iso, generate_id,
    calculate_wallet_balances, calculate_referral_bonus, calculate_referral_tier
)
import logging
import base64

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/portal', tags=['Portal'])

def simple_decrypt(encrypted: str) -> str:
    """Simple base64 decode for credentials."""
    if not encrypted:
        return ''
    try:
        return base64.b64decode(encrypted).decode('utf-8')
    except:
        return encrypted

def simple_encrypt(plain: str) -> str:
    """Simple base64 encode for credentials."""
    if not plain:
        return ''
    return base64.b64encode(plain.encode('utf-8')).decode('utf-8')

def check_visibility(client: dict, feature: str) -> bool:
    """
    Check if a feature is visible for the client based on visibility_level.
    
    HIDDEN: Only basic info (name, status)
    SUMMARY: Basic info + balance totals (no transaction details)
    FULL: Everything visible
    """
    level = client.get('visibility_level', 'full')
    
    if level == 'hidden':
        # Only basic profile info
        return feature in ['profile', 'basic']
    elif level == 'summary':
        # Profile + balances, but no transaction details or credentials
        return feature in ['profile', 'basic', 'balances', 'summary']
    else:  # 'full'
        return True

def apply_visibility_filter(client: dict, data: dict, feature: str) -> dict:
    """Apply visibility filtering to response data."""
    level = client.get('visibility_level', 'full')
    
    if level == 'full':
        return data
    
    if level == 'hidden':
        # Return minimal data
        return {'message': 'Details are hidden for your account'}
    
    if level == 'summary' and feature == 'dashboard':
        # Return summary without transaction details
        return {
            'wallet': {
                'real_balance': data.get('wallet', {}).get('real_balance', 0),
                'bonus_balance': data.get('wallet', {}).get('bonus_balance', 0),
            },
            'overview': {
                'lifetime_total_in': data.get('overview', {}).get('lifetime_total_in', 0),
                'lifetime_total_out': data.get('overview', {}).get('lifetime_total_out', 0),
            },
            'recent_transactions': [],  # Hidden in summary mode
            'referral_summary': data.get('referral_summary', {}),
            'bonus_info': data.get('bonus_info', {})
        }
    
    return data

# ==================== CLIENT PASSWORD AUTH ====================

@router.post('/auth/login', response_model=ClientPasswordLoginResponse)
async def client_password_login(login_data: ClientPasswordLogin):
    """Login with username/password (for clients who set up password auth)."""
    client = await authenticate_client_password(login_data.username, login_data.password)
    
    if not client:
        return ClientPasswordLoginResponse(
            success=False,
            message='Invalid username or password'
        )
    
    # Create JWT token
    access_token = await create_client_access_token(client['client_id'])
    
    return ClientPasswordLoginResponse(
        success=True,
        message='Login successful',
        client_id=client['client_id'],
        access_token=access_token,
        display_name=client.get('display_name')
    )

@router.post('/auth/setup-password')
async def setup_client_password(
    setup_data: ClientPasswordSetup,
    client: dict = Depends(get_portal_client_flexible)
):
    """Set up username/password for the current client (requires existing auth)."""
    db = await get_database()
    
    # Check if username is already taken
    existing = await db.clients.find_one({'username': setup_data.username.lower()}, {'_id': 0})
    if existing and existing['client_id'] != client['client_id']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Username already taken')
    
    # Hash password and update client
    password_hash = hash_password(setup_data.password)
    
    await db.clients.update_one(
        {'client_id': client['client_id']},
        {'$set': {
            'username': setup_data.username.lower(),
            'password_hash': password_hash,
            'password_auth_enabled': True,
            'password_set_at': get_current_utc_iso()
        }}
    )
    
    return {
        'success': True,
        'message': 'Password authentication set up successfully',
        'username': setup_data.username.lower()
    }

@router.get('/auth/status')
async def get_auth_status(client: dict = Depends(get_portal_client_flexible)):
    """Check if client has password auth enabled."""
    return {
        'client_id': client['client_id'],
        'display_name': client.get('display_name'),
        'password_auth_enabled': client.get('password_auth_enabled', False),
        'username': client.get('username')
    }

# ==================== PUBLIC VALIDATION ====================

@router.get('/validate/{token}')
async def validate_token(token: str):
    """Validate a portal token (public endpoint)."""
    client = await validate_portal_token(token)
    
    if not client:
        return {'valid': False, 'message': 'Invalid or expired portal link'}
    
    return {
        'valid': True,
        'client': {
            'client_id': client['client_id'],
            'display_name': client.get('display_name'),
            'status': client.get('status', 'active')
        }
    }


@router.get('/me', response_model=ClientResponse)
async def get_my_profile(client: dict = Depends(get_portal_client_flexible)):
    """Get current client profile."""
    return ClientResponse(**client)


@router.get('/dashboard')
async def get_dashboard(client: dict = Depends(get_portal_client_flexible)):
    """Get portal dashboard data with wallet balances."""
    db = await get_database()
    client_id = client['client_id']
    
    # Check visibility
    visibility = client.get('visibility_level', 'full')
    
    if visibility == 'hidden':
        return {
            'visibility_restricted': True,
            'message': 'Dashboard details are hidden for your account',
            'wallet': {'real_balance': 0, 'bonus_balance': 0},
            'overview': {},
            'recent_transactions': [],
            'referral_summary': {'referral_code': client.get('referral_code')},
            'bonus_info': {}
        }
    
    # Get wallet balances
    wallet = await calculate_wallet_balances(db, client_id)
    
    # Recent transactions (hidden in summary mode)
    recent_txs = []
    if visibility == 'full':
        recent_txs = await db.ledger_transactions.find(
            {'client_id': client_id},
            {'_id': 0}
        ).sort('created_at', -1).limit(10).to_list(10)
    
    # Referral stats
    referral_count = await db.client_referrals.count_documents({'referrer_client_id': client_id})
    valid_referrals = await db.client_referrals.count_documents(
        {'referrer_client_id': client_id, 'status': 'valid'}
    )
    
    # Calculate tier info
    tier_info = calculate_referral_tier(valid_referrals)
    bonus_info = calculate_referral_bonus(valid_referrals, client.get('bonus_claims', 0))
    
    return {
        'visibility_level': visibility,
        'wallet': {
            'real_balance': wallet['real_balance'],
            'bonus_balance': wallet['bonus_balance'],
            'total_in': wallet['total_in'] if visibility == 'full' else None,
            'total_out': wallet['total_out'] if visibility == 'full' else None,
            'pending_in': wallet['pending_in'] if visibility == 'full' else None,
            'pending_out': wallet['pending_out'] if visibility == 'full' else None
        },
        'overview': {
            'lifetime_total_in': wallet['total_in'] if visibility == 'full' else None,
            'lifetime_total_out': wallet['total_out'] if visibility == 'full' else None,
            'net_flow': wallet['real_balance'],
            'referral_earnings': wallet['referral_earnings'] if visibility == 'full' else None,
            'bonus_earnings': wallet['total_bonus_earned'] if visibility == 'full' else None
        },
        'recent_transactions': recent_txs,
        'referral_summary': {
            'referral_code': client.get('referral_code'),
            'total_referrals': referral_count,
            'valid_referrals': valid_referrals,
            'active_referrals': valid_referrals,
            'referred_by': client.get('referred_by_code'),
            'tier': tier_info['tier'],
            'percentage': tier_info['percentage'],
            'next_tier_at': tier_info['next_tier_at'],
            'progress_to_next': tier_info['progress_to_next']
        },
        'bonus_info': {
            'next_bonus_at': bonus_info['next_bonus_at'],
            'next_bonus_amount': bonus_info['next_bonus_amount'],
            'referrals_until_next': bonus_info['referrals_until_next'],
            'total_bonus_earned': wallet['total_bonus_earned']
        }
    }


@router.get('/wallets', response_model=WalletSummary)
async def get_wallet_summary(client: dict = Depends(get_portal_client_flexible)):
    """Get detailed wallet summary."""
    db = await get_database()
    
    # Check visibility
    if client.get('visibility_level') == 'hidden':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Wallet details are hidden for your account')
    
    wallet = await calculate_wallet_balances(db, client['client_id'])
    return WalletSummary(**wallet)


@router.get('/transactions', response_model=List[LedgerTransactionResponse])
async def get_my_transactions(
    type_filter: Optional[str] = None,
    wallet_type: Optional[str] = None,
    limit: int = 100,
    client: dict = Depends(get_portal_client_flexible)
):
    """Get client's transaction history."""
    db = await get_database()
    
    # Check visibility - transactions require FULL visibility
    visibility = client.get('visibility_level', 'full')
    if visibility != 'full':
        return []  # Return empty list for restricted visibility
    
    query = {'client_id': client['client_id']}
    
    if type_filter and type_filter in ['IN', 'OUT', 'ADJUST', 'REFERRAL_EARN', 'REAL_LOAD', 'BONUS_EARN', 'BONUS_LOAD']:
        query['type'] = type_filter
    
    if wallet_type and wallet_type in ['real', 'bonus']:
        if wallet_type == 'real':
            query['type'] = {'$in': ['IN', 'OUT', 'ADJUST', 'REFERRAL_EARN', 'REAL_LOAD']}
        else:
            query['type'] = {'$in': ['BONUS_EARN', 'BONUS_LOAD', 'BONUS_ADJUST']}
    
    transactions = await db.ledger_transactions.find(
        query,
        {'_id': 0}
    ).sort('created_at', -1).to_list(limit)
    
    return [LedgerTransactionResponse(**tx) for tx in transactions]


@router.get('/credentials', response_model=List[ClientCredentialResponse])
async def get_my_credentials(client: dict = Depends(get_portal_client_flexible)):
    """Get client's game credentials (masked by default)."""
    db = await get_database()
    
    # Check visibility - credentials require FULL visibility
    visibility = client.get('visibility_level', 'full')
    if visibility != 'full':
        return []  # Return empty list for restricted visibility
    
    credentials = await db.client_credentials.find(
        {'client_id': client['client_id']},
        {'_id': 0}
    ).to_list(100)
    
    if not credentials:
        return []
    
    # Get game names
    game_ids = [c['game_id'] for c in credentials]
    games = await db.games.find({'id': {'$in': game_ids}}, {'_id': 0}).to_list(100)
    games_map = {g['id']: g for g in games}
    
    result = []
    for cred in credentials:
        game = games_map.get(cred['game_id'], {})
        
        # Decrypt and mask credentials
        decrypted_user = simple_decrypt(cred.get('game_user_id', ''))
        decrypted_pass = simple_decrypt(cred.get('game_password', ''))
        
        masked_user = mask_credential(decrypted_user) if decrypted_user else '[Not Set]'
        masked_pass = mask_credential(decrypted_pass) if decrypted_pass else '[Not Set]'
        
        if not game.get('is_active', False):
            masked_user = '[Game Suspended]'
            masked_pass = '[Game Suspended]'
        
        result.append(ClientCredentialResponse(
            id=cred['id'],
            client_id=cred['client_id'],
            game_id=cred['game_id'],
            game_name=game.get('name', 'Unknown'),
            game_user_id=masked_user,
            game_password=masked_pass,
            is_active=cred.get('is_active', False) and game.get('is_active', False),
            assigned_at=cred['assigned_at'],
            last_accessed_at=cred.get('last_accessed_at')
        ))
    
    return result


@router.post('/credentials/{game_id}/reveal')
async def reveal_credential(game_id: str, client: dict = Depends(get_portal_client_flexible)):
    """Reveal full credentials for a game."""
    db = await get_database()
    
    # Check visibility - credentials require FULL visibility
    if client.get('visibility_level', 'full') != 'full':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Credentials are hidden for your account')
    
    game = await db.games.find_one({'id': game_id}, {'_id': 0})
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Game not found')
    
    if not game.get('is_active', False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Game is suspended')
    
    credential = await db.client_credentials.find_one(
        {'client_id': client['client_id'], 'game_id': game_id},
        {'_id': 0}
    )
    
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No credentials for this game')
    
    decrypted_user = simple_decrypt(credential.get('game_user_id', ''))
    decrypted_pass = simple_decrypt(credential.get('game_password', ''))
    
    if not decrypted_user or not decrypted_pass:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Credentials not yet assigned')
    
    await db.client_credentials.update_one(
        {'id': credential['id']},
        {'$set': {'last_accessed_at': get_current_utc_iso()}}
    )
    
    return {
        'game_user_id': decrypted_user,
        'game_password': decrypted_pass,
        'expires_in_seconds': 15
    }


# ==================== LOAD TO GAME ====================

@router.get('/games')
async def get_available_games(client: dict = Depends(get_portal_client_flexible)):
    """Get list of games available for loading."""
    db = await get_database()
    
    # Get active games
    games = await db.games.find({'is_active': True}, {'_id': 0}).to_list(100)
    
    # Get client's credentials
    credentials = await db.client_credentials.find(
        {'client_id': client['client_id']},
        {'_id': 0, 'game_id': 1, 'is_active': 1}
    ).to_list(100)
    cred_map = {c['game_id']: c for c in credentials}
    
    result = []
    for game in games:
        cred = cred_map.get(game['id'])
        result.append({
            'id': game['id'],
            'name': game['name'],
            'description': game.get('description', ''),
            'category': game.get('category'),
            'thumbnail': game.get('thumbnail'),
            'has_credentials': cred is not None and cred.get('is_active', False)
        })
    
    return {'games': result}


@router.post('/load-to-game', response_model=LoadToGameResponse)
async def load_to_game(
    request: LoadToGameRequest,
    client: dict = Depends(get_portal_client_flexible)
):
    """Submit a load-to-game request."""
    db = await get_database()
    client_id = client['client_id']
    
    # Check if client is allowed to load
    if client.get('load_locked'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Loading is currently disabled for your account')
    
    # Check if bonus wallet is locked
    if request.wallet_type == WalletType.BONUS and client.get('bonus_locked'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Bonus wallet is currently locked')
    
    # Validate game exists
    game = await db.games.find_one({'id': request.game_id, 'is_active': True}, {'_id': 0})
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Game not found or inactive')
    
    # Check credentials exist
    credential = await db.client_credentials.find_one(
        {'client_id': client_id, 'game_id': request.game_id, 'is_active': True},
        {'_id': 0}
    )
    if not credential:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No active credentials for this game')
    
    # Get wallet balances
    wallet = await calculate_wallet_balances(db, client_id)
    
    # Check sufficient balance
    if request.wallet_type == WalletType.REAL:
        if wallet['real_balance'] < request.amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Insufficient real wallet balance')
    else:
        if wallet['bonus_balance'] < request.amount:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Insufficient bonus wallet balance')
    
    # Validate amount
    if request.amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Amount must be greater than 0')
    
    # Create order
    order_id = generate_id()
    order_doc = {
        'order_id': order_id,
        'client_id': client_id,
        'order_type': 'load',
        'game': game['name'],
        'game_id': request.game_id,
        'amount': request.amount,
        'wallet_type': request.wallet_type.value,
        'status': OrderStatus.PENDING_CONFIRMATION.value,
        'created_at': get_current_utc_iso()
    }
    await db.orders.insert_one(order_doc)
    
    # Create pending transaction
    tx_type = TransactionType.REAL_LOAD if request.wallet_type == WalletType.REAL else TransactionType.BONUS_LOAD
    tx_doc = {
        'transaction_id': generate_id(),
        'client_id': client_id,
        'type': tx_type.value,
        'amount': request.amount,
        'wallet_type': request.wallet_type.value,
        'status': TransactionStatus.PENDING.value,
        'source': 'portal',
        'order_id': order_id,
        'reason': f"Load to {game['name']}",
        'created_at': get_current_utc_iso()
    }
    await db.ledger_transactions.insert_one(tx_doc)
    
    return LoadToGameResponse(
        order_id=order_id,
        client_id=client_id,
        game_id=request.game_id,
        game_name=game['name'],
        amount=request.amount,
        wallet_type=request.wallet_type,
        status=OrderStatus.PENDING_CONFIRMATION,
        message='Load request submitted. Awaiting confirmation.'
    )


@router.get('/load-history')
async def get_load_history(client: dict = Depends(get_portal_client_flexible)):
    """Get client's load-to-game history."""
    db = await get_database()
    
    # Check visibility
    if client.get('visibility_level', 'full') != 'full':
        return {'loads': []}  # Return empty for restricted visibility
    
    orders = await db.orders.find(
        {'client_id': client['client_id'], 'order_type': 'load'},
        {'_id': 0}
    ).sort('created_at', -1).to_list(100)
    
    return {'loads': orders}


# ==================== REFERRALS ====================

@router.get('/referrals')
async def get_my_referrals(client: dict = Depends(get_portal_client_flexible)):
    """Get client's referral information with bonus progress."""
    db = await get_database()
    client_id = client['client_id']
    
    # Referral info is available in all visibility modes
    # but detailed earnings may be hidden
    
    referrals = await db.client_referrals.find(
        {'referrer_client_id': client_id},
        {'_id': 0}
    ).sort('created_at', -1).to_list(100)
    
    # Calculate total earnings from referrals
    earnings_pipeline = [
        {'$match': {
            'client_id': client_id,
            'type': TransactionType.REFERRAL_EARN.value,
            'status': TransactionStatus.CONFIRMED.value
        }},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ]
    
    earnings_result = await db.ledger_transactions.aggregate(earnings_pipeline).to_list(1)
    total_earnings = earnings_result[0]['total'] if earnings_result else 0
    
    # Calculate bonus earnings
    bonus_pipeline = [
        {'$match': {
            'client_id': client_id,
            'type': TransactionType.BONUS_EARN.value,
            'source': 'referral_bonus',
            'status': TransactionStatus.CONFIRMED.value
        }},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ]
    
    bonus_result = await db.ledger_transactions.aggregate(bonus_pipeline).to_list(1)
    total_bonus = bonus_result[0]['total'] if bonus_result else 0
    
    # Get referred clients info
    referred_ids = [r['referred_client_id'] for r in referrals]
    referred_clients = await db.clients.find(
        {'client_id': {'$in': referred_ids}},
        {'_id': 0, 'client_id': 1, 'display_name': 1, 'created_at': 1}
    ).to_list(100)
    clients_map = {c['client_id']: c for c in referred_clients}
    
    valid_count = sum(1 for r in referrals if r.get('status') == 'valid')
    
    # Calculate tier and bonus info
    tier_info = calculate_referral_tier(valid_count)
    bonus_info = calculate_referral_bonus(valid_count, client.get('bonus_claims', 0))
    
    enriched_referrals = []
    for ref in referrals:
        referred = clients_map.get(ref['referred_client_id'], {})
        enriched_referrals.append({
            'id': ref['id'],
            'referred_display_name': referred.get('display_name', 'Player'),
            'status': ref.get('status', 'pending'),
            'total_deposits': ref.get('total_deposits', 0),
            'created_at': ref['created_at']
        })
    
    return {
        'referral_code': client.get('referral_code'),
        'referred_by': client.get('referred_by_code'),
        'referral_locked': client.get('referral_locked', False),
        'total_referrals': len(referrals),
        'valid_referrals': valid_count,
        'active_referrals': valid_count,
        'total_earnings': total_earnings,
        'total_bonus_earned': total_bonus,
        'tier': tier_info['tier'],
        'percentage': tier_info['percentage'],
        'next_tier_at': tier_info['next_tier_at'],
        'progress_to_next_tier': tier_info['progress_to_next'],
        'bonus_info': {
            'next_bonus_at': bonus_info['next_bonus_at'],
            'next_bonus_amount': bonus_info['next_bonus_amount'],
            'referrals_until_next': bonus_info['referrals_until_next'],
            'total_bonus_eligible': bonus_info['total_bonus_eligible']
        },
        'referrals': enriched_referrals
    }


@router.post('/referrals/apply', response_model=ApplyReferralResponse)
async def apply_referral_code_endpoint(
    referral_data: ApplyReferralRequest,
    client: dict = Depends(get_portal_client_flexible)
):
    """Apply a referral code from the portal."""
    db = await get_database()
    
    result = await apply_referral_code(db, client['client_id'], referral_data.referral_code)
    
    if result['success']:
        updated_client = await db.clients.find_one({'client_id': client['client_id']}, {'_id': 0})
        return ApplyReferralResponse(
            success=True,
            message=result['message'],
            referral_code=referral_data.referral_code.upper(),
            referred_by=updated_client.get('referred_by_code')
        )
    
    return ApplyReferralResponse(
        success=False,
        message=result['message']
    )


# ==================== WITHDRAWALS ====================

@router.get('/withdrawals')
async def get_my_withdrawals(client: dict = Depends(get_portal_client_flexible)):
    """Get client's withdrawal/redeem history."""
    db = await get_database()
    
    # Check visibility
    if client.get('visibility_level', 'full') != 'full':
        return {'withdrawals': []}  # Return empty for restricted visibility
    
    orders = await db.orders.find(
        {'client_id': client['client_id'], 'order_type': 'redeem'},
        {'_id': 0}
    ).sort('created_at', -1).to_list(100)
    
    return {'withdrawals': orders}


# ==================== BONUS TASKS / CLAIMS ====================

@router.get('/bonus-tasks')
async def get_bonus_tasks(client: dict = Depends(get_portal_client_flexible)):
    """Get available bonus tasks and progress."""
    db = await get_database()
    client_id = client['client_id']
    
    # Get referral stats
    valid_referrals = await db.client_referrals.count_documents(
        {'referrer_client_id': client_id, 'status': 'valid'}
    )
    
    # Calculate bonus info
    bonus_info = calculate_referral_bonus(valid_referrals, client.get('bonus_claims', 0))
    
    # Get bonus history
    bonus_history = await db.ledger_transactions.find(
        {
            'client_id': client_id,
            'type': TransactionType.BONUS_EARN.value,
            'source': 'referral_bonus'
        },
        {'_id': 0}
    ).sort('created_at', -1).to_list(20)
    
    tasks = []
    
    # Referral Milestone Task
    tasks.append({
        'id': 'referral_milestone',
        'title': 'Referral Milestone Bonus',
        'description': f'Get {bonus_info["next_bonus_at"]} valid referrals to earn ${bonus_info["next_bonus_amount"]:.2f} bonus',
        'type': 'referral',
        'progress': valid_referrals,
        'target': bonus_info['next_bonus_at'],
        'reward_amount': bonus_info['next_bonus_amount'],
        'status': 'in_progress' if bonus_info['referrals_until_next'] > 0 else 'claimable',
        'remaining': bonus_info['referrals_until_next']
    })
    
    return {
        'tasks': tasks,
        'bonus_history': bonus_history,
        'wallet_bonus_balance': (await calculate_wallet_balances(db, client_id))['bonus_balance']
    }
