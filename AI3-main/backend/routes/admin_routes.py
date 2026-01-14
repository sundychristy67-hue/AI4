from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from datetime import datetime, timezone
from models import (
    AdminDashboardStats, ClientResponse, ClientUpdate, ClientStatus,
    OrderResponse, OrderStatus, GameResponse, GameCreate, GameUpdate,
    ClientCredentialAssign, AdminCredentialUpdate, AdminWalletAdjustment,
    AdminOrderEdit, TransactionType, TransactionStatus, WalletType
)
from auth import get_current_admin
from database import get_database
from utils import generate_id, get_current_utc_iso, calculate_wallet_balances, process_referral_on_deposit
import logging
import base64

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/admin', tags=['Admin'])

def simple_encrypt(plain: str) -> str:
    if not plain:
        return ''
    return base64.b64encode(plain.encode('utf-8')).decode('utf-8')

async def log_admin_action(db, admin_id: str, action: str, entity_type: str, entity_id: str, details: dict):
    """Log admin actions for audit."""
    log_doc = {
        'id': generate_id(),
        'admin_id': admin_id,
        'action': action,
        'entity_type': entity_type,
        'entity_id': entity_id,
        'details': details,
        'timestamp': get_current_utc_iso()
    }
    await db.audit_logs.insert_one(log_doc)


@router.get('/dashboard-stats', response_model=AdminDashboardStats)
async def get_dashboard_stats(current_user: dict = Depends(get_current_admin)):
    """Get admin dashboard statistics."""
    db = await get_database()
    
    # Count stats
    total_users = await db.users.count_documents({})
    active_users = await db.users.count_documents({'is_active': True})
    total_clients = await db.clients.count_documents({})
    active_clients = await db.clients.count_documents({'status': 'active'})
    total_games = await db.games.count_documents({})
    
    pending_orders = await db.orders.count_documents(
        {'status': {'$in': ['pending_confirmation', 'pending_payout', 'pending_screenshot']}}
    )
    
    pending_withdrawals = await db.orders.count_documents(
        {'order_type': 'redeem', 'status': {'$in': ['pending_confirmation', 'pending_payout']}}
    )
    
    pending_loads = await db.orders.count_documents(
        {'order_type': 'load', 'status': 'pending_confirmation'}
    )
    
    # Calculate ledger totals
    ledger_in_pipeline = [
        {'$match': {'type': 'IN', 'status': 'confirmed'}},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ]
    ledger_in_result = await db.ledger_transactions.aggregate(ledger_in_pipeline).to_list(1)
    total_ledger_in = ledger_in_result[0]['total'] if ledger_in_result else 0
    
    ledger_out_pipeline = [
        {'$match': {'type': 'OUT', 'status': 'confirmed'}},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ]
    ledger_out_result = await db.ledger_transactions.aggregate(ledger_out_pipeline).to_list(1)
    total_ledger_out = ledger_out_result[0]['total'] if ledger_out_result else 0
    
    # Referral earnings
    referral_pipeline = [
        {'$match': {'type': 'REFERRAL_EARN', 'status': 'confirmed'}},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ]
    referral_result = await db.ledger_transactions.aggregate(referral_pipeline).to_list(1)
    total_earnings = referral_result[0]['total'] if referral_result else 0
    
    # Bonus distributed
    bonus_pipeline = [
        {'$match': {'type': 'BONUS_EARN', 'status': 'confirmed'}},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ]
    bonus_result = await db.ledger_transactions.aggregate(bonus_pipeline).to_list(1)
    total_bonus = bonus_result[0]['total'] if bonus_result else 0
    
    return AdminDashboardStats(
        total_users=total_users,
        active_users=active_users,
        total_clients=total_clients,
        active_clients=active_clients,
        total_games=total_games,
        pending_withdrawals=pending_withdrawals,
        pending_orders=pending_orders,
        pending_loads=pending_loads,
        total_withdrawals_amount=total_ledger_out,
        total_earnings_distributed=total_earnings,
        total_bonus_distributed=total_bonus,
        total_ledger_in=total_ledger_in,
        total_ledger_out=total_ledger_out
    )


@router.get('/attention-required')
async def get_attention_items(current_user: dict = Depends(get_current_admin)):
    """Get items requiring admin attention."""
    db = await get_database()
    items = []
    
    # Pending orders
    pending_orders = await db.orders.count_documents(
        {'status': {'$in': ['pending_confirmation', 'pending_payout']}}
    )
    if pending_orders > 0:
        items.append({
            'id': 'pending-orders',
            'title': f'{pending_orders} Pending Orders',
            'description': 'Orders awaiting confirmation or payout',
            'priority': 'high',
            'action_url': '/admin/orders'
        })
    
    # Pending loads
    pending_loads = await db.orders.count_documents(
        {'order_type': 'load', 'status': 'pending_confirmation'}
    )
    if pending_loads > 0:
        items.append({
            'id': 'pending-loads',
            'title': f'{pending_loads} Pending Load Requests',
            'description': 'Load-to-game requests awaiting confirmation',
            'priority': 'high',
            'action_url': '/admin/orders?filter=load'
        })
    
    # Suspected fraud referrals
    suspected_referrals = await db.client_referrals.count_documents({'status': 'suspected'})
    if suspected_referrals > 0:
        items.append({
            'id': 'suspected-fraud',
            'title': f'{suspected_referrals} Suspected Fraud Referrals',
            'description': 'Referrals flagged for review',
            'priority': 'high',
            'action_url': '/admin/referrals'
        })
    
    # Credentials not set
    empty_creds = await db.client_credentials.count_documents(
        {'$or': [{'game_user_id': ''}, {'game_password': ''}]}
    )
    if empty_creds > 0:
        items.append({
            'id': 'empty-credentials',
            'title': f'{empty_creds} Credentials Not Set',
            'description': 'Client credentials need to be assigned',
            'priority': 'medium',
            'action_url': '/admin/clients'
        })
    
    return {'items': items}


@router.get('/clients', response_model=List[ClientResponse])
async def get_clients(
    status_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_admin)
):
    """Get all clients."""
    db = await get_database()
    
    query = {}
    if status_filter:
        query['status'] = status_filter
    
    clients = await db.clients.find(query, {'_id': 0}).sort('created_at', -1).to_list(1000)
    return [ClientResponse(**c) for c in clients]


@router.get('/clients/{client_id}')
async def get_client_detail(client_id: str, current_user: dict = Depends(get_current_admin)):
    """Get detailed client information with wallet balances."""
    db = await get_database()
    
    client = await db.clients.find_one({'client_id': client_id}, {'_id': 0})
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Client not found')
    
    # Get wallet balances
    wallet = await calculate_wallet_balances(db, client_id)
    
    # Get credentials
    credentials = await db.client_credentials.find(
        {'client_id': client_id},
        {'_id': 0}
    ).to_list(100)
    
    # Get game names
    game_ids = [c['game_id'] for c in credentials]
    games = await db.games.find({'id': {'$in': game_ids}}, {'_id': 0}).to_list(100)
    games_map = {g['id']: g for g in games}
    
    for cred in credentials:
        cred['game_name'] = games_map.get(cred['game_id'], {}).get('name', 'Unknown')
    
    # Recent transactions
    transactions = await db.ledger_transactions.find(
        {'client_id': client_id},
        {'_id': 0}
    ).sort('created_at', -1).limit(20).to_list(20)
    
    # Recent orders
    orders = await db.orders.find(
        {'client_id': client_id},
        {'_id': 0}
    ).sort('created_at', -1).limit(20).to_list(20)
    
    # Referral info
    referrals = await db.client_referrals.find(
        {'referrer_client_id': client_id},
        {'_id': 0}
    ).to_list(100)
    
    return {
        'client': client,
        'wallet': wallet,
        'financial_summary': {
            'real_balance': wallet['real_balance'],
            'bonus_balance': wallet['bonus_balance'],
            'total_in': wallet['total_in'],
            'total_out': wallet['total_out'],
            'referral_earnings': wallet['referral_earnings'],
            'total_bonus_earned': wallet['total_bonus_earned'],
            'net_balance': wallet['real_balance']
        },
        'credentials': credentials,
        'recent_transactions': transactions,
        'recent_orders': orders,
        'referrals': referrals
    }


@router.put('/clients/{client_id}', response_model=ClientResponse)
async def update_client(
    client_id: str,
    update_data: ClientUpdate,
    current_user: dict = Depends(get_current_admin)
):
    """Update client."""
    db = await get_database()
    
    client = await db.clients.find_one({'client_id': client_id}, {'_id': 0})
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Client not found')
    
    update_fields = {}
    if update_data.display_name is not None:
        update_fields['display_name'] = update_data.display_name
    if update_data.status is not None:
        update_fields['status'] = update_data.status.value
    if update_data.withdraw_locked is not None:
        update_fields['withdraw_locked'] = update_data.withdraw_locked
    if update_data.load_locked is not None:
        update_fields['load_locked'] = update_data.load_locked
    if update_data.bonus_locked is not None:
        update_fields['bonus_locked'] = update_data.bonus_locked
    
    if update_fields:
        await db.clients.update_one({'client_id': client_id}, {'$set': update_fields})
        await log_admin_action(db, current_user['id'], 'client_update', 'client', client_id, update_fields)
    
    updated_client = await db.clients.find_one({'client_id': client_id}, {'_id': 0})
    return ClientResponse(**updated_client)


@router.post('/clients/{client_id}/adjust-wallet')
async def adjust_client_wallet(
    client_id: str,
    adjustment: AdminWalletAdjustment,
    current_user: dict = Depends(get_current_admin)
):
    """Adjust client's wallet balance (creates ADJUST or BONUS_ADJUST transaction)."""
    db = await get_database()
    
    client = await db.clients.find_one({'client_id': client_id}, {'_id': 0})
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Client not found')
    
    tx_type = TransactionType.ADJUST if adjustment.wallet_type == WalletType.REAL else TransactionType.BONUS_ADJUST
    
    tx_doc = {
        'transaction_id': generate_id(),
        'client_id': client_id,
        'type': tx_type.value,
        'amount': adjustment.amount,
        'wallet_type': adjustment.wallet_type.value,
        'status': TransactionStatus.CONFIRMED.value,
        'source': 'admin_adjust',
        'reason': adjustment.reason,
        'metadata': {'adjusted_by': current_user['id']},
        'created_at': get_current_utc_iso(),
        'confirmed_at': get_current_utc_iso(),
        'confirmed_by': current_user['id']
    }
    
    await db.ledger_transactions.insert_one(tx_doc)
    await log_admin_action(db, current_user['id'], 'wallet_adjust', 'client', client_id, {
        'wallet_type': adjustment.wallet_type.value,
        'amount': adjustment.amount,
        'reason': adjustment.reason
    })
    
    # Get updated balances
    wallet = await calculate_wallet_balances(db, client_id)
    
    return {
        'message': 'Wallet adjusted successfully',
        'transaction_id': tx_doc['transaction_id'],
        'new_balances': wallet
    }


@router.put('/clients/{client_id}/referral-count')
async def update_referral_count(
    client_id: str,
    valid_referral_count: int,
    current_user: dict = Depends(get_current_admin)
):
    """Manually update client's valid referral count."""
    db = await get_database()
    
    client = await db.clients.find_one({'client_id': client_id}, {'_id': 0})
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Client not found')
    
    await db.clients.update_one(
        {'client_id': client_id},
        {'$set': {'valid_referral_count': valid_referral_count}}
    )
    
    await log_admin_action(db, current_user['id'], 'referral_count_update', 'client', client_id, {
        'old_count': client.get('valid_referral_count', 0),
        'new_count': valid_referral_count
    })
    
    return {'message': 'Referral count updated', 'valid_referral_count': valid_referral_count}


@router.post('/clients/{client_id}/credentials')
async def set_client_credentials(
    client_id: str,
    cred_data: ClientCredentialAssign,
    current_user: dict = Depends(get_current_admin)
):
    """Assign or update game credentials for a client."""
    db = await get_database()
    
    client = await db.clients.find_one({'client_id': client_id}, {'_id': 0})
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Client not found')
    
    game = await db.games.find_one({'id': cred_data.game_id}, {'_id': 0})
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Game not found')
    
    # Check for existing credential
    existing = await db.client_credentials.find_one(
        {'client_id': client_id, 'game_id': cred_data.game_id}
    )
    
    encrypted_user = simple_encrypt(cred_data.game_user_id)
    encrypted_pass = simple_encrypt(cred_data.game_password)
    
    if existing:
        await db.client_credentials.update_one(
            {'client_id': client_id, 'game_id': cred_data.game_id},
            {'$set': {
                'game_user_id': encrypted_user,
                'game_password': encrypted_pass,
                'is_active': True
            }}
        )
    else:
        cred_doc = {
            'id': generate_id(),
            'client_id': client_id,
            'game_id': cred_data.game_id,
            'game_user_id': encrypted_user,
            'game_password': encrypted_pass,
            'is_active': True,
            'assigned_at': get_current_utc_iso(),
            'last_accessed_at': None
        }
        await db.client_credentials.insert_one(cred_doc)
    
    await log_admin_action(db, current_user['id'], 'credential_assign', 'client_credential', client_id, {'game_id': cred_data.game_id})
    
    return {'message': 'Credentials assigned successfully'}


# ==================== ORDERS MANAGEMENT ====================

@router.get('/orders', response_model=List[OrderResponse])
async def get_orders(
    status_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_admin)
):
    """Get all orders."""
    db = await get_database()
    
    query = {}
    if status_filter:
        query['status'] = status_filter
    if type_filter:
        query['order_type'] = type_filter
    
    orders = await db.orders.find(query, {'_id': 0}).sort('created_at', -1).to_list(1000)
    return [OrderResponse(**o) for o in orders]


@router.get('/orders/{order_id}')
async def get_order_detail(order_id: str, current_user: dict = Depends(get_current_admin)):
    """Get order details."""
    db = await get_database()
    
    order = await db.orders.find_one({'order_id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found')
    
    # Get related transaction
    transaction = await db.ledger_transactions.find_one({'order_id': order_id}, {'_id': 0})
    
    # Get client info
    client = await db.clients.find_one({'client_id': order['client_id']}, {'_id': 0})
    
    return {
        'order': order,
        'transaction': transaction,
        'client': client
    }


@router.put('/orders/{order_id}/edit')
async def edit_order_amount(
    order_id: str,
    edit_data: AdminOrderEdit,
    current_user: dict = Depends(get_current_admin)
):
    """Edit order amount before confirmation."""
    db = await get_database()
    
    order = await db.orders.find_one({'order_id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found')
    
    if order['status'] not in ['pending_confirmation', 'pending_payout', 'pending_screenshot']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Order cannot be edited in current status')
    
    original_amount = order.get('original_amount') or order['amount']
    
    await db.orders.update_one(
        {'order_id': order_id},
        {'$set': {
            'amount': edit_data.new_amount,
            'original_amount': original_amount
        }}
    )
    
    # Update related transaction
    await db.ledger_transactions.update_one(
        {'order_id': order_id},
        {'$set': {
            'amount': edit_data.new_amount,
            'original_amount': original_amount
        }}
    )
    
    await log_admin_action(db, current_user['id'], 'order_edit', 'order', order_id, {
        'original_amount': original_amount,
        'new_amount': edit_data.new_amount,
        'reason': edit_data.reason
    })
    
    return {'message': 'Order amount updated', 'new_amount': edit_data.new_amount}


@router.post('/orders/{order_id}/confirm')
async def confirm_order(order_id: str, current_user: dict = Depends(get_current_admin)):
    """Confirm an order and its related transaction."""
    db = await get_database()
    
    order = await db.orders.find_one({'order_id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found')
    
    if order['status'] not in ['pending_confirmation', 'pending_payout', 'pending_screenshot']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Order cannot be confirmed in current status')
    
    now = get_current_utc_iso()
    
    # Update order
    await db.orders.update_one(
        {'order_id': order_id},
        {'$set': {
            'status': OrderStatus.CONFIRMED.value,
            'confirmed_at': now,
            'confirmed_by': current_user['id']
        }}
    )
    
    # Update related transaction
    await db.ledger_transactions.update_one(
        {'order_id': order_id},
        {'$set': {
            'status': TransactionStatus.CONFIRMED.value,
            'confirmed_at': now,
            'confirmed_by': current_user['id']
        }}
    )
    
    # Process referral on deposit confirmation
    if order['order_type'] == 'load' and order.get('type') == 'IN':
        await process_referral_on_deposit(db, order['client_id'], order['amount'])
    
    await log_admin_action(db, current_user['id'], 'order_confirm', 'order', order_id, {'amount': order['amount']})
    
    return {'message': 'Order confirmed successfully'}


@router.post('/orders/{order_id}/reject')
async def reject_order(
    order_id: str,
    reason: str = "Rejected by admin",
    current_user: dict = Depends(get_current_admin)
):
    """Reject an order."""
    db = await get_database()
    
    order = await db.orders.find_one({'order_id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found')
    
    if order['status'] not in ['pending_confirmation', 'pending_payout', 'pending_screenshot']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Order cannot be rejected in current status')
    
    now = get_current_utc_iso()
    
    await db.orders.update_one(
        {'order_id': order_id},
        {'$set': {
            'status': OrderStatus.REJECTED.value,
            'rejection_reason': reason,
            'confirmed_at': now,
            'confirmed_by': current_user['id']
        }}
    )
    
    await db.ledger_transactions.update_one(
        {'order_id': order_id},
        {'$set': {
            'status': TransactionStatus.REJECTED.value,
            'confirmed_at': now,
            'confirmed_by': current_user['id']
        }}
    )
    
    await log_admin_action(db, current_user['id'], 'order_reject', 'order', order_id, {'reason': reason})
    
    return {'message': 'Order rejected'}


# ==================== GAMES MANAGEMENT ====================

@router.get('/games', response_model=List[GameResponse])
async def get_games(current_user: dict = Depends(get_current_admin)):
    """Get all games."""
    db = await get_database()
    games = await db.games.find({}, {'_id': 0}).sort([('display_order', 1), ('created_at', -1)]).to_list(100)
    return [GameResponse(**g) for g in games]


@router.post('/games', response_model=GameResponse)
async def create_game(game_data: GameCreate, current_user: dict = Depends(get_current_admin)):
    """Create a new game."""
    db = await get_database()
    
    # Get max display order
    max_order_game = await db.games.find_one({}, {'display_order': 1}, sort=[('display_order', -1)])
    next_order = (max_order_game.get('display_order', 0) if max_order_game else 0) + 1
    
    game_id = generate_id()
    game_doc = {
        'id': game_id,
        'name': game_data.name,
        'description': game_data.description,
        'tagline': game_data.tagline,
        'thumbnail': game_data.thumbnail,
        'icon_url': game_data.icon_url,
        'category': game_data.category,
        'download_url': game_data.download_url,
        'platforms': [p.value for p in game_data.platforms],
        'availability_status': game_data.availability_status.value,
        'show_credentials': game_data.show_credentials,
        'allow_recharge': game_data.allow_recharge,
        'is_featured': game_data.is_featured,
        'display_order': next_order,
        'is_active': True,
        'created_by': current_user['id'],
        'created_at': datetime.now(timezone.utc)
    }
    
    await db.games.insert_one(game_doc)
    await log_admin_action(db, current_user['id'], 'game_create', 'game', game_id, {'name': game_data.name})
    
    return GameResponse(**game_doc)


@router.put('/games/{game_id}', response_model=GameResponse)
async def update_game(
    game_id: str,
    game_data: GameUpdate,
    current_user: dict = Depends(get_current_admin)
):
    """Update a game."""
    db = await get_database()
    
    game = await db.games.find_one({'id': game_id}, {'_id': 0})
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Game not found')
    
    update_fields = {}
    if game_data.name is not None:
        update_fields['name'] = game_data.name
    if game_data.description is not None:
        update_fields['description'] = game_data.description
    if game_data.tagline is not None:
        update_fields['tagline'] = game_data.tagline
    if game_data.thumbnail is not None:
        update_fields['thumbnail'] = game_data.thumbnail
    if game_data.icon_url is not None:
        update_fields['icon_url'] = game_data.icon_url
    if game_data.category is not None:
        update_fields['category'] = game_data.category
    if game_data.download_url is not None:
        update_fields['download_url'] = game_data.download_url
    if game_data.platforms is not None:
        update_fields['platforms'] = [p.value for p in game_data.platforms]
    if game_data.availability_status is not None:
        update_fields['availability_status'] = game_data.availability_status.value
    if game_data.show_credentials is not None:
        update_fields['show_credentials'] = game_data.show_credentials
    if game_data.allow_recharge is not None:
        update_fields['allow_recharge'] = game_data.allow_recharge
    if game_data.is_featured is not None:
        update_fields['is_featured'] = game_data.is_featured
    if game_data.display_order is not None:
        update_fields['display_order'] = game_data.display_order
    if game_data.is_active is not None:
        update_fields['is_active'] = game_data.is_active
    
    if update_fields:
        await db.games.update_one({'id': game_id}, {'$set': update_fields})
        await log_admin_action(db, current_user['id'], 'game_update', 'game', game_id, update_fields)
    
    updated_game = await db.games.find_one({'id': game_id}, {'_id': 0})
    return GameResponse(**updated_game)


@router.put('/games/reorder')
async def reorder_games(
    game_orders: List[dict],
    current_user: dict = Depends(get_current_admin)
):
    """Update display order for multiple games. Expects: [{id: "...", order: 1}, ...]"""
    db = await get_database()
    
    for item in game_orders:
        await db.games.update_one(
            {'id': item['id']},
            {'$set': {'display_order': item['order']}}
        )
    
    await log_admin_action(db, current_user['id'], 'games_reorder', 'games', 'bulk', {'count': len(game_orders)})
    
    return {'message': 'Games reordered successfully'}


@router.delete('/games/{game_id}')
async def delete_game(
    game_id: str,
    current_user: dict = Depends(get_current_admin)
):
    """Soft delete a game (set inactive)."""
    db = await get_database()
    
    game = await db.games.find_one({'id': game_id}, {'_id': 0})
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Game not found')
    
    await db.games.update_one({'id': game_id}, {'$set': {'is_active': False}})
    await log_admin_action(db, current_user['id'], 'game_delete', 'game', game_id, {'name': game.get('name')})
    
    return {'message': 'Game deleted successfully'}


# ==================== REFERRAL MANAGEMENT ====================

@router.get('/referrals')
async def get_referrals(
    status_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_admin)
):
    """Get all referrals."""
    db = await get_database()
    
    query = {}
    if status_filter:
        query['status'] = status_filter
    
    referrals = await db.client_referrals.find(query, {'_id': 0}).sort('created_at', -1).to_list(500)
    
    # Get client info
    referrer_ids = list(set([r['referrer_client_id'] for r in referrals]))
    referred_ids = list(set([r['referred_client_id'] for r in referrals]))
    all_ids = list(set(referrer_ids + referred_ids))
    
    clients = await db.clients.find({'client_id': {'$in': all_ids}}, {'_id': 0}).to_list(500)
    clients_map = {c['client_id']: c for c in clients}
    
    result = []
    for ref in referrals:
        referrer = clients_map.get(ref['referrer_client_id'], {})
        referred = clients_map.get(ref['referred_client_id'], {})
        result.append({
            **ref,
            'referrer_name': referrer.get('display_name', 'Unknown'),
            'referred_name': referred.get('display_name', 'Unknown')
        })
    
    return {'referrals': result}


@router.put('/referrals/{referral_id}/status')
async def update_referral_status(
    referral_id: str,
    new_status: str,
    current_user: dict = Depends(get_current_admin)
):
    """Update referral status (valid, fraud, suspected)."""
    db = await get_database()
    
    if new_status not in ['pending', 'valid', 'fraud', 'suspected']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid status')
    
    referral = await db.client_referrals.find_one({'id': referral_id}, {'_id': 0})
    if not referral:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Referral not found')
    
    old_status = referral.get('status')
    
    await db.client_referrals.update_one(
        {'id': referral_id},
        {'$set': {'status': new_status}}
    )
    
    # Update valid referral count if status changed to/from valid
    if old_status == 'valid' and new_status != 'valid':
        await db.clients.update_one(
            {'client_id': referral['referrer_client_id']},
            {'$inc': {'valid_referral_count': -1}}
        )
    elif old_status != 'valid' and new_status == 'valid':
        await db.clients.update_one(
            {'client_id': referral['referrer_client_id']},
            {'$inc': {'valid_referral_count': 1}}
        )
    
    await log_admin_action(db, current_user['id'], 'referral_status_update', 'referral', referral_id, {
        'old_status': old_status,
        'new_status': new_status
    })
    
    return {'message': 'Referral status updated'}


# ==================== AUDIT LOGS ====================

@router.get('/audit-logs')
async def get_audit_logs(
    limit: int = 100,
    current_user: dict = Depends(get_current_admin)
):
    """Get admin audit logs."""
    db = await get_database()
    logs = await db.audit_logs.find({}, {'_id': 0}).sort('timestamp', -1).to_list(limit)
    return {'logs': logs}
