"""
Telegram Routes - Webhook endpoints for Telegram bot
PostgreSQL Version
"""
from fastapi import APIRouter, HTTPException, status, Header
from typing import Optional
from config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/telegram', tags=['Telegram'])


async def verify_internal_api(x_internal_api_key: str = Header(None)):
    """Verify internal API key."""
    if x_internal_api_key != settings.internal_api_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid internal API key')
    return True


@router.post('/cash-in')
async def handle_cash_in(
    client_id: str,
    amount: float,
    payment_method: Optional[str] = None,
    _: bool = None  # Depends(verify_internal_api)
):
    """Handle cash-in request from Telegram bot."""
    from database import fetch_one, execute, row_to_dict
    from utils import generate_id, get_current_utc
    
    client = await fetch_one("SELECT * FROM clients WHERE client_id = $1", client_id)
    if not client:
        raise HTTPException(status_code=404, detail='Client not found')
    
    order_id = generate_id()
    tx_id = generate_id()
    now = get_current_utc()
    
    await execute(
        """
        INSERT INTO orders (order_id, client_id, order_type, game, amount, payment_method, status, created_at)
        VALUES ($1, $2, 'create', 'Cash In', $3, $4, 'pending_confirmation', $5)
        """,
        order_id, client_id, amount, payment_method, now
    )
    
    await execute(
        """
        INSERT INTO ledger_transactions (transaction_id, client_id, type, amount, wallet_type, status, source, order_id, reason, created_at)
        VALUES ($1, $2, 'IN', $3, 'real', 'pending', 'telegram_cashin', $4, 'Cash in via Telegram', $5)
        """,
        tx_id, client_id, amount, order_id, now
    )
    
    return {
        'order_id': order_id,
        'transaction_id': tx_id,
        'status': 'pending_confirmation',
        'message': 'Cash-in request created'
    }


@router.post('/cash-out')
async def handle_cash_out(
    client_id: str,
    amount: float,
    payout_tag: Optional[str] = None,
    _: bool = None
):
    """Handle cash-out request from Telegram bot."""
    from database import fetch_one, execute
    from utils import generate_id, get_current_utc, calculate_wallet_balances
    from database import get_pool
    
    pool = await get_pool()
    
    client = await fetch_one("SELECT * FROM clients WHERE client_id = $1", client_id)
    if not client:
        raise HTTPException(status_code=404, detail='Client not found')
    
    wallet = await calculate_wallet_balances(pool, client_id)
    if wallet['real_balance'] < amount:
        raise HTTPException(status_code=400, detail='Insufficient balance')
    
    order_id = generate_id()
    tx_id = generate_id()
    now = get_current_utc()
    
    await execute(
        """
        INSERT INTO orders (order_id, client_id, order_type, game, amount, payout_tag, status, created_at)
        VALUES ($1, $2, 'redeem', 'Cash Out', $3, $4, 'pending_confirmation', $5)
        """,
        order_id, client_id, amount, payout_tag, now
    )
    
    await execute(
        """
        INSERT INTO ledger_transactions (transaction_id, client_id, type, amount, wallet_type, status, source, order_id, reason, created_at)
        VALUES ($1, $2, 'OUT', $3, 'real', 'pending', 'telegram_cashout', $4, 'Cash out via Telegram', $5)
        """,
        tx_id, client_id, amount, order_id, now
    )
    
    return {
        'order_id': order_id,
        'transaction_id': tx_id,
        'status': 'pending_confirmation',
        'message': 'Cash-out request created'
    }


@router.post('/load')
async def handle_load_request(
    client_id: str,
    game_id: str,
    amount: float,
    wallet_type: str = "real",
    _: bool = None
):
    """Handle load-to-game request from Telegram bot."""
    from database import fetch_one, execute
    from utils import generate_id, get_current_utc, calculate_wallet_balances
    from database import get_pool, row_to_dict
    
    pool = await get_pool()
    
    client = await fetch_one("SELECT * FROM clients WHERE client_id = $1", client_id)
    if not client:
        raise HTTPException(status_code=404, detail='Client not found')
    
    game = await fetch_one("SELECT * FROM games WHERE id = $1 AND is_active = TRUE", game_id)
    if not game:
        raise HTTPException(status_code=404, detail='Game not found')
    
    game = row_to_dict(game)
    wallet = await calculate_wallet_balances(pool, client_id)
    
    balance_key = 'real_balance' if wallet_type == 'real' else 'bonus_balance'
    if wallet[balance_key] < amount:
        raise HTTPException(status_code=400, detail=f'Insufficient {wallet_type} balance')
    
    order_id = generate_id()
    tx_id = generate_id()
    now = get_current_utc()
    tx_type = 'REAL_LOAD' if wallet_type == 'real' else 'BONUS_LOAD'
    
    await execute(
        """
        INSERT INTO orders (order_id, client_id, order_type, game, game_id, amount, wallet_type, status, created_at)
        VALUES ($1, $2, 'load', $3, $4, $5, $6, 'pending_confirmation', $7)
        """,
        order_id, client_id, game['name'], game_id, amount, wallet_type, now
    )
    
    await execute(
        """
        INSERT INTO ledger_transactions (transaction_id, client_id, type, amount, wallet_type, status, source, order_id, reason, created_at)
        VALUES ($1, $2, $3, $4, $5, 'pending', 'telegram_load', $6, $7, $8)
        """,
        tx_id, client_id, tx_type, amount, wallet_type, order_id, f"Load to {game['name']}", now
    )
    
    return {
        'order_id': order_id,
        'transaction_id': tx_id,
        'game_name': game['name'],
        'status': 'pending_confirmation',
        'message': 'Load request created'
    }


@router.get('/pending-orders')
async def get_pending_orders(_: bool = None):
    """Get all pending orders for Telegram bot to display."""
    from database import fetch_all, rows_to_list
    
    orders = await fetch_all(
        """
        SELECT o.*, c.display_name as client_name 
        FROM orders o
        LEFT JOIN clients c ON o.client_id = c.client_id
        WHERE o.status IN ('pending_confirmation', 'pending_payout')
        ORDER BY o.created_at DESC
        LIMIT 50
        """
    )
    
    result = []
    for o in rows_to_list(orders):
        if o.get('created_at'):
            o['created_at'] = o['created_at'].isoformat()
        result.append(o)
    
    return {'orders': result}


@router.post('/confirm/{order_id}')
async def confirm_order(order_id: str, _: bool = None):
    """Confirm an order from Telegram bot."""
    from database import fetch_one, execute, row_to_dict
    from utils import get_current_utc
    
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    if not order:
        raise HTTPException(status_code=404, detail='Order not found')
    
    order = row_to_dict(order)
    if order['status'] not in ['pending_confirmation', 'pending_payout']:
        raise HTTPException(status_code=400, detail='Order cannot be confirmed')
    
    now = get_current_utc()
    
    await execute(
        "UPDATE orders SET status = 'confirmed', confirmed_at = $1, confirmed_by = 'telegram_bot' WHERE order_id = $2",
        now, order_id
    )
    
    await execute(
        "UPDATE ledger_transactions SET status = 'confirmed', confirmed_at = $1, confirmed_by = 'telegram_bot' WHERE order_id = $2",
        now, order_id
    )
    
    return {'order_id': order_id, 'status': 'confirmed', 'message': 'Order confirmed'}


@router.post('/reject/{order_id}')
async def reject_order(order_id: str, reason: str = "Rejected via Telegram", _: bool = None):
    """Reject an order from Telegram bot."""
    from database import fetch_one, execute, row_to_dict
    from utils import get_current_utc
    
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    if not order:
        raise HTTPException(status_code=404, detail='Order not found')
    
    order = row_to_dict(order)
    if order['status'] not in ['pending_confirmation', 'pending_payout']:
        raise HTTPException(status_code=400, detail='Order cannot be rejected')
    
    now = get_current_utc()
    
    await execute(
        "UPDATE orders SET status = 'rejected', rejection_reason = $1, confirmed_at = $2, confirmed_by = 'telegram_bot' WHERE order_id = $3",
        reason, now, order_id
    )
    
    await execute(
        "UPDATE ledger_transactions SET status = 'rejected', confirmed_at = $1, confirmed_by = 'telegram_bot' WHERE order_id = $2",
        now, order_id
    )
    
    return {'order_id': order_id, 'status': 'rejected', 'message': 'Order rejected'}


@router.post('/edit/{order_id}')
async def edit_order_amount(order_id: str, new_amount: float, _: bool = None):
    """Edit order amount from Telegram bot."""
    from database import fetch_one, execute, row_to_dict
    
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    if not order:
        raise HTTPException(status_code=404, detail='Order not found')
    
    order = row_to_dict(order)
    if order['status'] not in ['pending_confirmation', 'pending_payout']:
        raise HTTPException(status_code=400, detail='Order cannot be edited')
    
    original = order.get('original_amount') or order['amount']
    
    await execute(
        "UPDATE orders SET amount = $1, original_amount = $2 WHERE order_id = $3",
        new_amount, original, order_id
    )
    
    await execute(
        "UPDATE ledger_transactions SET amount = $1, original_amount = $2 WHERE order_id = $3",
        new_amount, original, order_id
    )
    
    return {
        'order_id': order_id,
        'original_amount': original,
        'new_amount': new_amount,
        'message': 'Order amount updated'
    }
