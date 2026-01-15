from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from datetime import datetime, timezone
import json
from models import (
    AdminDashboardStats, ClientResponse, ClientUpdate, ClientStatus,
    OrderResponse, OrderStatus, GameResponse, GameCreate, GameUpdate,
    ClientCredentialAssign, AdminCredentialUpdate, AdminWalletAdjustment,
    AdminOrderEdit, TransactionType, TransactionStatus, WalletType
)
from auth import get_current_admin
from database import fetch_one, fetch_all, execute, row_to_dict, rows_to_list
from utils import generate_id, get_current_utc, get_current_utc_iso, calculate_wallet_balances, process_referral_on_deposit
import logging
import base64

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/admin', tags=['Admin'])

def simple_encrypt(plain: str) -> str:
    if not plain:
        return ''
    return base64.b64encode(plain.encode('utf-8')).decode('utf-8')

async def log_admin_action(admin_id: str, action: str, entity_type: str, entity_id: str, details: dict):
    """Log admin actions for audit."""
    log_id = generate_id()
    await execute(
        """
        INSERT INTO audit_logs (id, admin_id, action, entity_type, entity_id, details, timestamp)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """,
        log_id, admin_id, action, entity_type, entity_id, json.dumps(details), get_current_utc()
    )

@router.get('/dashboard-stats', response_model=AdminDashboardStats)
async def get_dashboard_stats(current_user: dict = Depends(get_current_admin)):
    """Get admin dashboard statistics."""
    total_users = (await fetch_one("SELECT COUNT(*) as count FROM users"))['count']
    active_users = (await fetch_one("SELECT COUNT(*) as count FROM users WHERE is_active = TRUE"))['count']
    total_clients = (await fetch_one("SELECT COUNT(*) as count FROM clients"))['count']
    active_clients = (await fetch_one("SELECT COUNT(*) as count FROM clients WHERE status = 'active'"))['count']
    total_games = (await fetch_one("SELECT COUNT(*) as count FROM games"))['count']
    
    pending_orders = (await fetch_one(
        "SELECT COUNT(*) as count FROM orders WHERE status IN ('pending_confirmation', 'pending_payout', 'pending_screenshot')"
    ))['count']
    
    pending_withdrawals = (await fetch_one(
        "SELECT COUNT(*) as count FROM orders WHERE order_type = 'redeem' AND status IN ('pending_confirmation', 'pending_payout')"
    ))['count']
    
    pending_loads = (await fetch_one(
        "SELECT COUNT(*) as count FROM orders WHERE order_type = 'load' AND status = 'pending_confirmation'"
    ))['count']
    
    ledger_in = await fetch_one("SELECT COALESCE(SUM(amount), 0) as total FROM ledger_transactions WHERE type = 'IN' AND status = 'confirmed'")
    total_ledger_in = ledger_in['total'] if ledger_in else 0
    
    ledger_out = await fetch_one("SELECT COALESCE(SUM(amount), 0) as total FROM ledger_transactions WHERE type = 'OUT' AND status = 'confirmed'")
    total_ledger_out = ledger_out['total'] if ledger_out else 0
    
    referral_earn = await fetch_one("SELECT COALESCE(SUM(amount), 0) as total FROM ledger_transactions WHERE type = 'REFERRAL_EARN' AND status = 'confirmed'")
    total_earnings = referral_earn['total'] if referral_earn else 0
    
    bonus_earn = await fetch_one("SELECT COALESCE(SUM(amount), 0) as total FROM ledger_transactions WHERE type = 'BONUS_EARN' AND status = 'confirmed'")
    total_bonus = bonus_earn['total'] if bonus_earn else 0
    
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
    items = []
    
    pending_orders = (await fetch_one(
        "SELECT COUNT(*) as count FROM orders WHERE status IN ('pending_confirmation', 'pending_payout')"
    ))['count']
    if pending_orders > 0:
        items.append({
            'id': 'pending-orders',
            'title': f'{pending_orders} Pending Orders',
            'description': 'Orders awaiting confirmation or payout',
            'priority': 'high',
            'action_url': '/admin/orders'
        })
    
    pending_loads = (await fetch_one(
        "SELECT COUNT(*) as count FROM orders WHERE order_type = 'load' AND status = 'pending_confirmation'"
    ))['count']
    if pending_loads > 0:
        items.append({
            'id': 'pending-loads',
            'title': f'{pending_loads} Pending Load Requests',
            'description': 'Load-to-game requests awaiting confirmation',
            'priority': 'high',
            'action_url': '/admin/orders?filter=load'
        })
    
    suspected_referrals = (await fetch_one(
        "SELECT COUNT(*) as count FROM client_referrals WHERE status = 'suspected'"
    ))['count']
    if suspected_referrals > 0:
        items.append({
            'id': 'suspected-fraud',
            'title': f'{suspected_referrals} Suspected Fraud Referrals',
            'description': 'Referrals flagged for review',
            'priority': 'high',
            'action_url': '/admin/referrals'
        })
    
    empty_creds = (await fetch_one(
        "SELECT COUNT(*) as count FROM client_credentials WHERE game_user_id = '' OR game_password = ''"
    ))['count']
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
async def get_clients(status_filter: Optional[str] = None, current_user: dict = Depends(get_current_admin)):
    """Get all clients."""
    if status_filter:
        clients = await fetch_all(
            "SELECT * FROM clients WHERE status = $1 ORDER BY created_at DESC LIMIT 1000",
            status_filter
        )
    else:
        clients = await fetch_all("SELECT * FROM clients ORDER BY created_at DESC LIMIT 1000")
    
    result = []
    for c in rows_to_list(clients):
        c['created_at'] = c['created_at'].isoformat() if c.get('created_at') else get_current_utc_iso()
        if c.get('last_active_at'):
            c['last_active_at'] = c['last_active_at'].isoformat()
        result.append(ClientResponse(**c))
    return result

@router.get('/clients/{client_id}')
async def get_client_detail(client_id: str, current_user: dict = Depends(get_current_admin)):
    """Get detailed client information with wallet balances."""
    from database import get_pool
    pool = await get_pool()
    
    client = await fetch_one("SELECT * FROM clients WHERE client_id = $1", client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Client not found')
    
    client = row_to_dict(client)
    if client.get('created_at'):
        client['created_at'] = client['created_at'].isoformat()
    if client.get('last_active_at'):
        client['last_active_at'] = client['last_active_at'].isoformat()
    
    wallet = await calculate_wallet_balances(pool, client_id)
    
    credentials = await fetch_all("SELECT * FROM client_credentials WHERE client_id = $1", client_id)
    credentials = rows_to_list(credentials)
    
    game_ids = [c['game_id'] for c in credentials]
    if game_ids:
        placeholders = ', '.join([f'${i+1}' for i in range(len(game_ids))])
        games = await fetch_all(f"SELECT * FROM games WHERE id IN ({placeholders})", *game_ids)
        games_map = {g['id']: g for g in rows_to_list(games)}
    else:
        games_map = {}
    
    for cred in credentials:
        cred['game_name'] = games_map.get(cred['game_id'], {}).get('name', 'Unknown')
        if cred.get('assigned_at'):
            cred['assigned_at'] = cred['assigned_at'].isoformat()
        if cred.get('last_accessed_at'):
            cred['last_accessed_at'] = cred['last_accessed_at'].isoformat()
    
    transactions = await fetch_all(
        "SELECT * FROM ledger_transactions WHERE client_id = $1 ORDER BY created_at DESC LIMIT 20",
        client_id
    )
    transactions = rows_to_list(transactions)
    for tx in transactions:
        if tx.get('created_at'):
            tx['created_at'] = tx['created_at'].isoformat()
        if tx.get('confirmed_at'):
            tx['confirmed_at'] = tx['confirmed_at'].isoformat()
    
    orders = await fetch_all(
        "SELECT * FROM orders WHERE client_id = $1 ORDER BY created_at DESC LIMIT 20",
        client_id
    )
    orders = rows_to_list(orders)
    for o in orders:
        if o.get('created_at'):
            o['created_at'] = o['created_at'].isoformat()
        if o.get('confirmed_at'):
            o['confirmed_at'] = o['confirmed_at'].isoformat()
    
    referrals = await fetch_all(
        "SELECT * FROM client_referrals WHERE referrer_client_id = $1",
        client_id
    )
    referrals = rows_to_list(referrals)
    for r in referrals:
        if r.get('created_at'):
            r['created_at'] = r['created_at'].isoformat()
    
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
async def update_client(client_id: str, update_data: ClientUpdate, current_user: dict = Depends(get_current_admin)):
    """Update client."""
    client = await fetch_one("SELECT * FROM clients WHERE client_id = $1", client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Client not found')
    
    updates = []
    params = []
    param_idx = 1
    
    if update_data.display_name is not None:
        updates.append(f"display_name = ${param_idx}")
        params.append(update_data.display_name)
        param_idx += 1
    if update_data.status is not None:
        updates.append(f"status = ${param_idx}")
        params.append(update_data.status.value)
        param_idx += 1
    if update_data.withdraw_locked is not None:
        updates.append(f"withdraw_locked = ${param_idx}")
        params.append(update_data.withdraw_locked)
        param_idx += 1
    if update_data.load_locked is not None:
        updates.append(f"load_locked = ${param_idx}")
        params.append(update_data.load_locked)
        param_idx += 1
    if update_data.bonus_locked is not None:
        updates.append(f"bonus_locked = ${param_idx}")
        params.append(update_data.bonus_locked)
        param_idx += 1
    if update_data.visibility_level is not None:
        updates.append(f"visibility_level = ${param_idx}")
        params.append(update_data.visibility_level.value)
        param_idx += 1
    
    if updates:
        params.append(client_id)
        await execute(
            f"UPDATE clients SET {', '.join(updates)} WHERE client_id = ${param_idx}",
            *params
        )
        await log_admin_action(current_user['id'], 'client_update', 'client', client_id, update_data.dict(exclude_none=True))
    
    updated = await fetch_one("SELECT * FROM clients WHERE client_id = $1", client_id)
    updated = row_to_dict(updated)
    updated['created_at'] = updated['created_at'].isoformat() if updated.get('created_at') else get_current_utc_iso()
    if updated.get('last_active_at'):
        updated['last_active_at'] = updated['last_active_at'].isoformat()
    return ClientResponse(**updated)

@router.post('/clients/{client_id}/adjust-wallet')
async def adjust_client_wallet(client_id: str, adjustment: AdminWalletAdjustment, current_user: dict = Depends(get_current_admin)):
    """Adjust client's wallet balance."""
    from database import get_pool
    pool = await get_pool()
    
    client = await fetch_one("SELECT * FROM clients WHERE client_id = $1", client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Client not found')
    
    tx_type = TransactionType.ADJUST if adjustment.wallet_type == WalletType.REAL else TransactionType.BONUS_ADJUST
    tx_id = generate_id()
    now = get_current_utc()
    
    await execute(
        """
        INSERT INTO ledger_transactions (transaction_id, client_id, type, amount, wallet_type, status, source, reason, metadata, created_at, confirmed_at, confirmed_by)
        VALUES ($1, $2, $3, $4, $5, 'confirmed', 'admin_adjust', $6, $7, $8, $8, $9)
        """,
        tx_id, client_id, tx_type.value, adjustment.amount, adjustment.wallet_type.value,
        adjustment.reason, json.dumps({'adjusted_by': current_user['id']}), now, current_user['id']
    )
    
    await log_admin_action(current_user['id'], 'wallet_adjust', 'client', client_id, {
        'wallet_type': adjustment.wallet_type.value,
        'amount': adjustment.amount,
        'reason': adjustment.reason
    })
    
    wallet = await calculate_wallet_balances(pool, client_id)
    
    return {'message': 'Wallet adjusted successfully', 'transaction_id': tx_id, 'new_balances': wallet}

@router.post('/clients/{client_id}/credentials')
async def set_client_credentials(client_id: str, cred_data: ClientCredentialAssign, current_user: dict = Depends(get_current_admin)):
    """Assign or update game credentials for a client."""
    client = await fetch_one("SELECT * FROM clients WHERE client_id = $1", client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Client not found')
    
    game = await fetch_one("SELECT * FROM games WHERE id = $1", cred_data.game_id)
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Game not found')
    
    existing = await fetch_one(
        "SELECT * FROM client_credentials WHERE client_id = $1 AND game_id = $2",
        client_id, cred_data.game_id
    )
    
    encrypted_user = simple_encrypt(cred_data.game_user_id)
    encrypted_pass = simple_encrypt(cred_data.game_password)
    
    if existing:
        await execute(
            "UPDATE client_credentials SET game_user_id = $1, game_password = $2, is_active = TRUE WHERE client_id = $3 AND game_id = $4",
            encrypted_user, encrypted_pass, client_id, cred_data.game_id
        )
    else:
        cred_id = generate_id()
        await execute(
            """
            INSERT INTO client_credentials (id, client_id, game_id, game_user_id, game_password, is_active, assigned_at)
            VALUES ($1, $2, $3, $4, $5, TRUE, $6)
            """,
            cred_id, client_id, cred_data.game_id, encrypted_user, encrypted_pass, get_current_utc()
        )
    
    await log_admin_action(current_user['id'], 'credential_assign', 'client_credential', client_id, {'game_id': cred_data.game_id})
    return {'message': 'Credentials assigned successfully'}

# ==================== ORDERS MANAGEMENT ====================

@router.get('/orders', response_model=List[OrderResponse])
async def get_orders(status_filter: Optional[str] = None, type_filter: Optional[str] = None, current_user: dict = Depends(get_current_admin)):
    """Get all orders."""
    query = "SELECT * FROM orders WHERE 1=1"
    params = []
    
    if status_filter:
        params.append(status_filter)
        query += f" AND status = ${len(params)}"
    if type_filter:
        params.append(type_filter)
        query += f" AND order_type = ${len(params)}"
    
    query += " ORDER BY created_at DESC LIMIT 1000"
    
    orders = await fetch_all(query, *params) if params else await fetch_all(query)
    
    result = []
    for o in rows_to_list(orders):
        o['created_at'] = o['created_at'].isoformat() if o.get('created_at') else get_current_utc_iso()
        if o.get('confirmed_at'):
            o['confirmed_at'] = o['confirmed_at'].isoformat()
        result.append(OrderResponse(**o))
    return result

@router.get('/orders/{order_id}')
async def get_order_detail(order_id: str, current_user: dict = Depends(get_current_admin)):
    """Get order details."""
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found')
    
    order = row_to_dict(order)
    if order.get('created_at'):
        order['created_at'] = order['created_at'].isoformat()
    if order.get('confirmed_at'):
        order['confirmed_at'] = order['confirmed_at'].isoformat()
    
    transaction = await fetch_one("SELECT * FROM ledger_transactions WHERE order_id = $1", order_id)
    if transaction:
        transaction = row_to_dict(transaction)
        if transaction.get('created_at'):
            transaction['created_at'] = transaction['created_at'].isoformat()
        if transaction.get('confirmed_at'):
            transaction['confirmed_at'] = transaction['confirmed_at'].isoformat()
    
    client = await fetch_one("SELECT * FROM clients WHERE client_id = $1", order['client_id'])
    if client:
        client = row_to_dict(client)
        if client.get('created_at'):
            client['created_at'] = client['created_at'].isoformat()
        if client.get('last_active_at'):
            client['last_active_at'] = client['last_active_at'].isoformat()
    
    return {'order': order, 'transaction': transaction, 'client': client}

@router.put('/orders/{order_id}/edit')
async def edit_order_amount(order_id: str, edit_data: AdminOrderEdit, current_user: dict = Depends(get_current_admin)):
    """Edit order amount before confirmation."""
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found')
    
    order = row_to_dict(order)
    if order['status'] not in ['pending_confirmation', 'pending_payout', 'pending_screenshot']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Order cannot be edited in current status')
    
    original_amount = order.get('original_amount') or order['amount']
    
    await execute(
        "UPDATE orders SET amount = $1, original_amount = $2 WHERE order_id = $3",
        edit_data.new_amount, original_amount, order_id
    )
    
    await execute(
        "UPDATE ledger_transactions SET amount = $1, original_amount = $2 WHERE order_id = $3",
        edit_data.new_amount, original_amount, order_id
    )
    
    await log_admin_action(current_user['id'], 'order_edit', 'order', order_id, {
        'original_amount': original_amount,
        'new_amount': edit_data.new_amount,
        'reason': edit_data.reason
    })
    
    return {'message': 'Order amount updated', 'new_amount': edit_data.new_amount}

@router.post('/orders/{order_id}/confirm')
async def confirm_order(order_id: str, current_user: dict = Depends(get_current_admin)):
    """Confirm an order and its related transaction."""
    from database import get_pool
    pool = await get_pool()
    
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found')
    
    order = row_to_dict(order)
    if order['status'] not in ['pending_confirmation', 'pending_payout', 'pending_screenshot']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Order cannot be confirmed in current status')
    
    now = get_current_utc()
    
    await execute(
        "UPDATE orders SET status = $1, confirmed_at = $2, confirmed_by = $3 WHERE order_id = $4",
        OrderStatus.CONFIRMED.value, now, current_user['id'], order_id
    )
    
    await execute(
        "UPDATE ledger_transactions SET status = $1, confirmed_at = $2, confirmed_by = $3 WHERE order_id = $4",
        TransactionStatus.CONFIRMED.value, now, current_user['id'], order_id
    )
    
    if order['order_type'] == 'load' and order.get('type') == 'IN':
        await process_referral_on_deposit(pool, order['client_id'], order['amount'])
    
    await log_admin_action(current_user['id'], 'order_confirm', 'order', order_id, {'amount': order['amount']})
    return {'message': 'Order confirmed successfully'}

@router.post('/orders/{order_id}/reject')
async def reject_order(order_id: str, reason: str = "Rejected by admin", current_user: dict = Depends(get_current_admin)):
    """Reject an order."""
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found')
    
    order = row_to_dict(order)
    if order['status'] not in ['pending_confirmation', 'pending_payout', 'pending_screenshot']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Order cannot be rejected in current status')
    
    now = get_current_utc()
    
    await execute(
        "UPDATE orders SET status = $1, rejection_reason = $2, confirmed_at = $3, confirmed_by = $4 WHERE order_id = $5",
        OrderStatus.REJECTED.value, reason, now, current_user['id'], order_id
    )
    
    await execute(
        "UPDATE ledger_transactions SET status = $1, confirmed_at = $2, confirmed_by = $3 WHERE order_id = $4",
        TransactionStatus.REJECTED.value, now, current_user['id'], order_id
    )
    
    await log_admin_action(current_user['id'], 'order_reject', 'order', order_id, {'reason': reason})
    return {'message': 'Order rejected'}

# ==================== GAMES MANAGEMENT ====================

@router.get('/games', response_model=List[GameResponse])
async def get_games(current_user: dict = Depends(get_current_admin)):
    """Get all games."""
    games = await fetch_all("SELECT * FROM games ORDER BY display_order ASC, created_at DESC")
    
    result = []
    for g in rows_to_list(games):
        g['created_at'] = g['created_at'] if g.get('created_at') else datetime.now(timezone.utc)
        result.append(GameResponse(**g))
    return result

@router.post('/games', response_model=GameResponse)
async def create_game(game_data: GameCreate, current_user: dict = Depends(get_current_admin)):
    """Create a new game."""
    max_order = await fetch_one("SELECT COALESCE(MAX(display_order), 0) as max_order FROM games")
    next_order = (max_order['max_order'] or 0) + 1
    
    game_id = generate_id()
    now = datetime.now(timezone.utc)
    
    await execute(
        """
        INSERT INTO games (id, name, description, tagline, thumbnail, icon_url, category, download_url, platforms, 
                          availability_status, show_credentials, allow_recharge, is_featured, display_order, is_active, created_by, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, TRUE, $15, $16)
        """,
        game_id, game_data.name, game_data.description, game_data.tagline, game_data.thumbnail,
        game_data.icon_url, game_data.category, game_data.download_url,
        [p.value for p in game_data.platforms], game_data.availability_status.value,
        game_data.show_credentials, game_data.allow_recharge, game_data.is_featured, next_order,
        current_user['id'], now
    )
    
    await log_admin_action(current_user['id'], 'game_create', 'game', game_id, {'name': game_data.name})
    
    game = await fetch_one("SELECT * FROM games WHERE id = $1", game_id)
    game = row_to_dict(game)
    return GameResponse(**game)

@router.put('/games/{game_id}', response_model=GameResponse)
async def update_game(game_id: str, game_data: GameUpdate, current_user: dict = Depends(get_current_admin)):
    """Update a game."""
    game = await fetch_one("SELECT * FROM games WHERE id = $1", game_id)
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Game not found')
    
    updates = []
    params = []
    param_idx = 1
    
    field_mapping = {
        'name': game_data.name, 'description': game_data.description, 'tagline': game_data.tagline,
        'thumbnail': game_data.thumbnail, 'icon_url': game_data.icon_url, 'category': game_data.category,
        'download_url': game_data.download_url, 'show_credentials': game_data.show_credentials,
        'allow_recharge': game_data.allow_recharge, 'is_featured': game_data.is_featured,
        'display_order': game_data.display_order, 'is_active': game_data.is_active
    }
    
    for field, value in field_mapping.items():
        if value is not None:
            updates.append(f"{field} = ${param_idx}")
            params.append(value)
            param_idx += 1
    
    if game_data.platforms is not None:
        updates.append(f"platforms = ${param_idx}")
        params.append([p.value for p in game_data.platforms])
        param_idx += 1
    
    if game_data.availability_status is not None:
        updates.append(f"availability_status = ${param_idx}")
        params.append(game_data.availability_status.value)
        param_idx += 1
    
    if updates:
        params.append(game_id)
        await execute(f"UPDATE games SET {', '.join(updates)} WHERE id = ${param_idx}", *params)
        await log_admin_action(current_user['id'], 'game_update', 'game', game_id, game_data.dict(exclude_none=True))
    
    updated = await fetch_one("SELECT * FROM games WHERE id = $1", game_id)
    return GameResponse(**row_to_dict(updated))

@router.delete('/games/{game_id}')
async def delete_game(game_id: str, current_user: dict = Depends(get_current_admin)):
    """Soft delete a game."""
    game = await fetch_one("SELECT * FROM games WHERE id = $1", game_id)
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Game not found')
    
    await execute("UPDATE games SET is_active = FALSE WHERE id = $1", game_id)
    await log_admin_action(current_user['id'], 'game_delete', 'game', game_id, {'name': row_to_dict(game).get('name')})
    return {'message': 'Game deleted successfully'}

# ==================== REFERRAL MANAGEMENT ====================

@router.get('/referrals')
async def get_referrals(status_filter: Optional[str] = None, current_user: dict = Depends(get_current_admin)):
    """Get all referrals."""
    if status_filter:
        referrals = await fetch_all(
            "SELECT * FROM client_referrals WHERE status = $1 ORDER BY created_at DESC LIMIT 500",
            status_filter
        )
    else:
        referrals = await fetch_all("SELECT * FROM client_referrals ORDER BY created_at DESC LIMIT 500")
    
    referrals = rows_to_list(referrals)
    
    all_ids = list(set([r['referrer_client_id'] for r in referrals] + [r['referred_client_id'] for r in referrals]))
    if all_ids:
        placeholders = ', '.join([f'${i+1}' for i in range(len(all_ids))])
        clients = await fetch_all(f"SELECT client_id, display_name FROM clients WHERE client_id IN ({placeholders})", *all_ids)
        clients_map = {c['client_id']: c for c in rows_to_list(clients)}
    else:
        clients_map = {}
    
    result = []
    for ref in referrals:
        referrer = clients_map.get(ref['referrer_client_id'], {})
        referred = clients_map.get(ref['referred_client_id'], {})
        ref['referrer_name'] = referrer.get('display_name', 'Unknown')
        ref['referred_name'] = referred.get('display_name', 'Unknown')
        if ref.get('created_at'):
            ref['created_at'] = ref['created_at'].isoformat()
        result.append(ref)
    
    return {'referrals': result}

@router.put('/referrals/{referral_id}/status')
async def update_referral_status(referral_id: str, new_status: str, current_user: dict = Depends(get_current_admin)):
    """Update referral status."""
    if new_status not in ['pending', 'valid', 'fraud', 'suspected']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid status')
    
    referral = await fetch_one("SELECT * FROM client_referrals WHERE id = $1", referral_id)
    if not referral:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Referral not found')
    
    referral = row_to_dict(referral)
    old_status = referral.get('status')
    
    await execute("UPDATE client_referrals SET status = $1 WHERE id = $2", new_status, referral_id)
    
    if old_status == 'valid' and new_status != 'valid':
        await execute(
            "UPDATE clients SET valid_referral_count = valid_referral_count - 1 WHERE client_id = $1",
            referral['referrer_client_id']
        )
    elif old_status != 'valid' and new_status == 'valid':
        await execute(
            "UPDATE clients SET valid_referral_count = valid_referral_count + 1 WHERE client_id = $1",
            referral['referrer_client_id']
        )
    
    await log_admin_action(current_user['id'], 'referral_status_update', 'referral', referral_id, {
        'old_status': old_status, 'new_status': new_status
    })
    
    return {'message': 'Referral status updated'}

# ==================== AUDIT LOGS ====================

@router.get('/audit-logs')
async def get_audit_logs(limit: int = 100, current_user: dict = Depends(get_current_admin)):
    """Get admin audit logs."""
    logs = await fetch_all("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT $1", limit)
    
    result = []
    for log in rows_to_list(logs):
        if log.get('timestamp'):
            log['timestamp'] = log['timestamp'].isoformat()
        result.append(log)
    
    return {'logs': result}
