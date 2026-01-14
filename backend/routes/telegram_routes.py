"""
Telegram Integration Routes

These endpoints are designed to be called by Telegram bots for:
- Cash-In confirmations (deposits)
- Cash-Out confirmations (withdrawals)
- Load confirmations
- Amount editing before confirmation

All endpoints require the internal API key for authentication.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, timezone
from models import TransactionType, TransactionStatus, OrderStatus, WalletType
from auth import verify_internal_api_key
from database import get_database
from utils import generate_id, get_current_utc_iso, process_referral_on_deposit
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/telegram', tags=['Telegram Integration'])


# ==================== REQUEST MODELS ====================

class CashInRequest(BaseModel):
    client_id: str
    amount: float
    game: Optional[str] = "General"
    payment_method: Optional[str] = None
    screenshot_url: Optional[str] = None
    telegram_message_id: Optional[str] = None

class CashOutRequest(BaseModel):
    client_id: str
    amount: float
    game: Optional[str] = "General"
    payout_tag: Optional[str] = None
    telegram_message_id: Optional[str] = None

class LoadRequest(BaseModel):
    client_id: str
    game_id: str
    amount: float
    wallet_type: WalletType = WalletType.REAL
    telegram_message_id: Optional[str] = None

class ConfirmRequest(BaseModel):
    confirmed_by: Optional[str] = "telegram_admin"

class EditAmountRequest(BaseModel):
    new_amount: float
    reason: str
    edited_by: Optional[str] = "telegram_admin"

class RejectRequest(BaseModel):
    reason: str
    rejected_by: Optional[str] = "telegram_admin"


# ==================== CASH-IN (DEPOSIT) ENDPOINTS ====================

@router.post('/cash-in')
async def create_cash_in(
    request: CashInRequest,
    _: bool = Depends(verify_internal_api_key)
):
    """
    Create a new cash-in (deposit) order.
    Called when a user sends a deposit screenshot via Telegram.
    """
    db = await get_database()
    
    # Verify client exists
    client = await db.clients.find_one({'client_id': request.client_id}, {'_id': 0})
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Client not found')
    
    if client.get('status') == 'banned':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Client is banned')
    
    # Create order
    order_id = generate_id()
    order_doc = {
        'order_id': order_id,
        'client_id': request.client_id,
        'order_type': 'create',  # Cash-in is a "create" type order
        'game': request.game,
        'amount': request.amount,
        'wallet_type': 'real',
        'payment_method': request.payment_method,
        'screenshot_url': request.screenshot_url,
        'status': OrderStatus.PENDING_CONFIRMATION.value,
        'telegram_message_id': request.telegram_message_id,
        'created_at': get_current_utc_iso()
    }
    await db.orders.insert_one(order_doc)
    
    # Create pending transaction
    tx_doc = {
        'transaction_id': generate_id(),
        'client_id': request.client_id,
        'type': TransactionType.IN.value,
        'amount': request.amount,
        'wallet_type': 'real',
        'status': TransactionStatus.PENDING.value,
        'source': 'telegram_cashin',
        'order_id': order_id,
        'reason': f'Deposit via {request.payment_method or "unknown"}',
        'created_at': get_current_utc_iso()
    }
    await db.ledger_transactions.insert_one(tx_doc)
    
    logger.info(f"Created cash-in order {order_id} for client {request.client_id}, amount: {request.amount}")
    
    return {
        'success': True,
        'order_id': order_id,
        'client_name': client.get('display_name'),
        'amount': request.amount,
        'status': 'pending_confirmation',
        'message': f'Cash-in order created. Amount: ${request.amount:.2f}'
    }


@router.post('/cash-in/{order_id}/confirm')
async def confirm_cash_in(
    order_id: str,
    request: ConfirmRequest,
    _: bool = Depends(verify_internal_api_key)
):
    """
    Confirm a cash-in order from Telegram.
    This credits the amount to the client's real wallet.
    """
    db = await get_database()
    
    order = await db.orders.find_one({'order_id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found')
    
    if order['status'] not in ['pending_confirmation', 'pending_screenshot']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Order cannot be confirmed in {order["status"]} status')
    
    now = get_current_utc_iso()
    
    # Update order
    await db.orders.update_one(
        {'order_id': order_id},
        {'$set': {
            'status': OrderStatus.CONFIRMED.value,
            'confirmed_at': now,
            'confirmed_by': request.confirmed_by
        }}
    )
    
    # Update transaction
    await db.ledger_transactions.update_one(
        {'order_id': order_id},
        {'$set': {
            'status': TransactionStatus.CONFIRMED.value,
            'confirmed_at': now,
            'confirmed_by': request.confirmed_by
        }}
    )
    
    # Process referral bonuses on deposit
    referral_result = await process_referral_on_deposit(db, order['client_id'], order['amount'])
    
    logger.info(f"Confirmed cash-in order {order_id}, amount: {order['amount']}")
    
    return {
        'success': True,
        'order_id': order_id,
        'amount_credited': order['amount'],
        'referral_activated': referral_result.get('referral_activated', False),
        'referrer_earned': referral_result.get('referrer_earned', 0),
        'bonus_credited': referral_result.get('bonus_credited', 0),
        'message': f'Confirmed! ${order["amount"]:.2f} credited to client wallet.'
    }


# ==================== CASH-OUT (WITHDRAWAL) ENDPOINTS ====================

@router.post('/cash-out')
async def create_cash_out(
    request: CashOutRequest,
    _: bool = Depends(verify_internal_api_key)
):
    """
    Create a new cash-out (withdrawal) order.
    Called when a user requests a withdrawal via Telegram.
    """
    db = await get_database()
    
    # Verify client exists
    client = await db.clients.find_one({'client_id': request.client_id}, {'_id': 0})
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Client not found')
    
    if client.get('status') == 'banned':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Client is banned')
    
    if client.get('withdraw_locked'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Withdrawals are locked for this client')
    
    # Check balance (get from ledger)
    from utils import calculate_wallet_balances
    wallet = await calculate_wallet_balances(db, request.client_id)
    
    if wallet['real_balance'] < request.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f'Insufficient balance. Available: ${wallet["real_balance"]:.2f}'
        )
    
    # Create order
    order_id = generate_id()
    order_doc = {
        'order_id': order_id,
        'client_id': request.client_id,
        'order_type': 'redeem',
        'game': request.game,
        'amount': request.amount,
        'wallet_type': 'real',
        'payout_tag': request.payout_tag,
        'status': OrderStatus.PENDING_CONFIRMATION.value,
        'telegram_message_id': request.telegram_message_id,
        'created_at': get_current_utc_iso()
    }
    await db.orders.insert_one(order_doc)
    
    # Create pending transaction
    tx_doc = {
        'transaction_id': generate_id(),
        'client_id': request.client_id,
        'type': TransactionType.OUT.value,
        'amount': request.amount,
        'wallet_type': 'real',
        'status': TransactionStatus.PENDING.value,
        'source': 'telegram_cashout',
        'order_id': order_id,
        'reason': f'Withdrawal to {request.payout_tag or "unknown"}',
        'created_at': get_current_utc_iso()
    }
    await db.ledger_transactions.insert_one(tx_doc)
    
    logger.info(f"Created cash-out order {order_id} for client {request.client_id}, amount: {request.amount}")
    
    return {
        'success': True,
        'order_id': order_id,
        'client_name': client.get('display_name'),
        'amount': request.amount,
        'payout_tag': request.payout_tag,
        'status': 'pending_confirmation',
        'message': f'Cash-out order created. Amount: ${request.amount:.2f}'
    }


@router.post('/cash-out/{order_id}/confirm')
async def confirm_cash_out(
    order_id: str,
    request: ConfirmRequest,
    _: bool = Depends(verify_internal_api_key)
):
    """
    Confirm a cash-out order from Telegram.
    This finalizes the withdrawal.
    """
    db = await get_database()
    
    order = await db.orders.find_one({'order_id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found')
    
    if order['status'] not in ['pending_confirmation', 'pending_payout']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Order cannot be confirmed in {order["status"]} status')
    
    now = get_current_utc_iso()
    
    await db.orders.update_one(
        {'order_id': order_id},
        {'$set': {
            'status': OrderStatus.CONFIRMED.value,
            'confirmed_at': now,
            'confirmed_by': request.confirmed_by
        }}
    )
    
    await db.ledger_transactions.update_one(
        {'order_id': order_id},
        {'$set': {
            'status': TransactionStatus.CONFIRMED.value,
            'confirmed_at': now,
            'confirmed_by': request.confirmed_by
        }}
    )
    
    logger.info(f"Confirmed cash-out order {order_id}, amount: {order['amount']}")
    
    return {
        'success': True,
        'order_id': order_id,
        'amount_withdrawn': order['amount'],
        'message': f'Confirmed! ${order["amount"]:.2f} withdrawal processed.'
    }


# ==================== LOAD TO GAME ENDPOINTS ====================

@router.post('/load')
async def create_load(
    request: LoadRequest,
    _: bool = Depends(verify_internal_api_key)
):
    """
    Create a load-to-game order from Telegram.
    """
    db = await get_database()
    
    # Verify client
    client = await db.clients.find_one({'client_id': request.client_id}, {'_id': 0})
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Client not found')
    
    if client.get('load_locked'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Loading is locked for this client')
    
    # Verify game
    game = await db.games.find_one({'id': request.game_id, 'is_active': True}, {'_id': 0})
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Game not found or inactive')
    
    # Check balance
    from utils import calculate_wallet_balances
    wallet = await calculate_wallet_balances(db, request.client_id)
    
    balance = wallet['real_balance'] if request.wallet_type == WalletType.REAL else wallet['bonus_balance']
    if balance < request.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Insufficient {request.wallet_type.value} wallet balance. Available: ${balance:.2f}'
        )
    
    # Create order
    order_id = generate_id()
    order_doc = {
        'order_id': order_id,
        'client_id': request.client_id,
        'order_type': 'load',
        'game': game['name'],
        'game_id': request.game_id,
        'amount': request.amount,
        'wallet_type': request.wallet_type.value,
        'status': OrderStatus.PENDING_CONFIRMATION.value,
        'telegram_message_id': request.telegram_message_id,
        'created_at': get_current_utc_iso()
    }
    await db.orders.insert_one(order_doc)
    
    # Create pending transaction
    tx_type = TransactionType.REAL_LOAD if request.wallet_type == WalletType.REAL else TransactionType.BONUS_LOAD
    tx_doc = {
        'transaction_id': generate_id(),
        'client_id': request.client_id,
        'type': tx_type.value,
        'amount': request.amount,
        'wallet_type': request.wallet_type.value,
        'status': TransactionStatus.PENDING.value,
        'source': 'telegram_load',
        'order_id': order_id,
        'reason': f'Load to {game["name"]}',
        'created_at': get_current_utc_iso()
    }
    await db.ledger_transactions.insert_one(tx_doc)
    
    logger.info(f"Created load order {order_id} for client {request.client_id}, game: {game['name']}, amount: {request.amount}")
    
    return {
        'success': True,
        'order_id': order_id,
        'client_name': client.get('display_name'),
        'game_name': game['name'],
        'amount': request.amount,
        'wallet_type': request.wallet_type.value,
        'status': 'pending_confirmation',
        'message': f'Load order created. ${request.amount:.2f} to {game["name"]}'
    }


@router.post('/load/{order_id}/confirm')
async def confirm_load(
    order_id: str,
    request: ConfirmRequest,
    _: bool = Depends(verify_internal_api_key)
):
    """
    Confirm a load order from Telegram.
    """
    db = await get_database()
    
    order = await db.orders.find_one({'order_id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found')
    
    if order['status'] != 'pending_confirmation':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'Order cannot be confirmed in {order["status"]} status')
    
    now = get_current_utc_iso()
    
    await db.orders.update_one(
        {'order_id': order_id},
        {'$set': {
            'status': OrderStatus.CONFIRMED.value,
            'confirmed_at': now,
            'confirmed_by': request.confirmed_by
        }}
    )
    
    await db.ledger_transactions.update_one(
        {'order_id': order_id},
        {'$set': {
            'status': TransactionStatus.CONFIRMED.value,
            'confirmed_at': now,
            'confirmed_by': request.confirmed_by
        }}
    )
    
    logger.info(f"Confirmed load order {order_id}")
    
    return {
        'success': True,
        'order_id': order_id,
        'message': f'Confirmed! ${order["amount"]:.2f} loaded to {order["game"]}.'
    }


# ==================== COMMON EDIT/REJECT ENDPOINTS ====================

@router.put('/order/{order_id}/edit')
async def edit_order_amount(
    order_id: str,
    request: EditAmountRequest,
    _: bool = Depends(verify_internal_api_key)
):
    """
    Edit the amount of a pending order before confirmation.
    This is the key feature for Telegram edit-before-confirm flow.
    """
    db = await get_database()
    
    order = await db.orders.find_one({'order_id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found')
    
    if order['status'] not in ['pending_confirmation', 'pending_payout', 'pending_screenshot']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Order cannot be edited in current status')
    
    if request.new_amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Amount must be greater than 0')
    
    original_amount = order.get('original_amount') or order['amount']
    
    # Update order
    await db.orders.update_one(
        {'order_id': order_id},
        {'$set': {
            'amount': request.new_amount,
            'original_amount': original_amount,
            'edit_reason': request.reason,
            'edited_by': request.edited_by,
            'edited_at': get_current_utc_iso()
        }}
    )
    
    # Update transaction
    await db.ledger_transactions.update_one(
        {'order_id': order_id},
        {'$set': {
            'amount': request.new_amount,
            'original_amount': original_amount
        }}
    )
    
    logger.info(f"Edited order {order_id} amount from {original_amount} to {request.new_amount}")
    
    return {
        'success': True,
        'order_id': order_id,
        'original_amount': original_amount,
        'new_amount': request.new_amount,
        'reason': request.reason,
        'message': f'Amount updated from ${original_amount:.2f} to ${request.new_amount:.2f}'
    }


@router.post('/order/{order_id}/reject')
async def reject_order(
    order_id: str,
    request: RejectRequest,
    _: bool = Depends(verify_internal_api_key)
):
    """
    Reject any pending order from Telegram.
    """
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
            'rejection_reason': request.reason,
            'confirmed_at': now,
            'confirmed_by': request.rejected_by
        }}
    )
    
    await db.ledger_transactions.update_one(
        {'order_id': order_id},
        {'$set': {
            'status': TransactionStatus.REJECTED.value,
            'confirmed_at': now,
            'confirmed_by': request.rejected_by
        }}
    )
    
    logger.info(f"Rejected order {order_id}: {request.reason}")
    
    return {
        'success': True,
        'order_id': order_id,
        'reason': request.reason,
        'message': 'Order rejected.'
    }


# ==================== QUERY ENDPOINTS ====================

@router.get('/pending-orders')
async def get_pending_orders(
    order_type: Optional[str] = None,
    _: bool = Depends(verify_internal_api_key)
):
    """
    Get all pending orders for Telegram bot to display.
    """
    db = await get_database()
    
    query = {'status': {'$in': ['pending_confirmation', 'pending_payout', 'pending_screenshot']}}
    if order_type:
        query['order_type'] = order_type
    
    orders = await db.orders.find(query, {'_id': 0}).sort('created_at', -1).to_list(100)
    
    # Enrich with client names
    client_ids = list(set([o['client_id'] for o in orders]))
    clients = await db.clients.find({'client_id': {'$in': client_ids}}, {'_id': 0}).to_list(100)
    clients_map = {c['client_id']: c for c in clients}
    
    result = []
    for order in orders:
        client = clients_map.get(order['client_id'], {})
        result.append({
            **order,
            'client_name': client.get('display_name', 'Unknown')
        })
    
    return {'orders': result, 'count': len(result)}


@router.get('/order/{order_id}')
async def get_order(
    order_id: str,
    _: bool = Depends(verify_internal_api_key)
):
    """
    Get order details for Telegram bot.
    """
    db = await get_database()
    
    order = await db.orders.find_one({'order_id': order_id}, {'_id': 0})
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Order not found')
    
    client = await db.clients.find_one({'client_id': order['client_id']}, {'_id': 0})
    transaction = await db.ledger_transactions.find_one({'order_id': order_id}, {'_id': 0})
    
    return {
        'order': order,
        'client': client,
        'transaction': transaction
    }


@router.get('/client/{client_id}/balance')
async def get_client_balance(
    client_id: str,
    _: bool = Depends(verify_internal_api_key)
):
    """
    Get client's wallet balances for Telegram bot.
    """
    db = await get_database()
    
    client = await db.clients.find_one({'client_id': client_id}, {'_id': 0})
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Client not found')
    
    from utils import calculate_wallet_balances
    wallet = await calculate_wallet_balances(db, client_id)
    
    return {
        'client_id': client_id,
        'client_name': client.get('display_name'),
        'real_balance': wallet['real_balance'],
        'bonus_balance': wallet['bonus_balance'],
        'pending_in': wallet['pending_in'],
        'pending_out': wallet['pending_out']
    }
