"""
Test Routes - AI Test Spot and Payment Simulation Panel
PostgreSQL Version
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, List
from datetime import datetime, timezone
import json
from auth import get_current_admin
from database import fetch_one, fetch_all, execute, row_to_dict, rows_to_list
from utils import generate_id, get_current_utc, get_current_utc_iso, generate_referral_code
from config import settings
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/test', tags=['Test'])


# ==================== AI TEST SPOT ====================

@router.post('/ai-test/simulate')
async def simulate_ai_response(
    prompt: str,
    scenario: str = "general",
    current_user: dict = Depends(get_current_admin)
):
    """
    Simulate AI response for testing (uses GPT-4o via Emergent LLM Key).
    This is a TEST environment - not for production use.
    """
    from emergentintegrations.llm.chat import chat, LlmModel
    
    emergent_key = settings.emergent_llm_key
    if not emergent_key:
        raise HTTPException(status_code=500, detail='Emergent LLM Key not configured')
    
    # Build context based on scenario
    system_prompts = {
        "general": "You are a helpful assistant for a gaming platform. Answer questions about games, accounts, and transactions.",
        "client_query": "You are a customer service agent for a gaming platform. Help clients with their questions about their account, balance, and referrals.",
        "agent_response": "You are an AI agent helping to automate responses. Be concise and professional.",
        "payment_flow": "You are helping to guide a client through a payment process. Be clear about steps and requirements.",
        "error_handling": "You are helping troubleshoot issues. Ask clarifying questions and suggest solutions."
    }
    
    system_prompt = system_prompts.get(scenario, system_prompts["general"])
    
    try:
        response = await chat(
            api_key=emergent_key,
            prompt=prompt,
            model=LlmModel.GPT_4O,
            system_prompt=system_prompt + "\n\n[TEST MODE - This is a test environment for AI behavior testing]"
        )
        
        # Log the test
        log_id = generate_id()
        await execute(
            """
            INSERT INTO ai_test_logs (id, admin_id, scenario, messages, created_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            log_id, current_user['id'], scenario,
            json.dumps([{"role": "user", "content": prompt}, {"role": "assistant", "content": response}]),
            get_current_utc()
        )
        
        return {
            'response': response,
            'scenario': scenario,
            'model': 'gpt-4o',
            'test_mode': True,
            'log_id': log_id
        }
        
    except Exception as e:
        logger.error(f"AI test error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI test failed: {str(e)}")


@router.get('/ai-test/logs')
async def get_ai_test_logs(
    limit: int = 50,
    current_user: dict = Depends(get_current_admin)
):
    """Get AI test logs."""
    logs = await fetch_all(
        "SELECT * FROM ai_test_logs ORDER BY created_at DESC LIMIT $1",
        limit
    )
    
    result = []
    for log in rows_to_list(logs):
        if log.get('created_at'):
            log['created_at'] = log['created_at'].isoformat()
        result.append(log)
    
    return {'logs': result}


@router.delete('/ai-test/logs')
async def clear_ai_test_logs(current_user: dict = Depends(get_current_admin)):
    """Clear all AI test logs."""
    await execute("DELETE FROM ai_test_logs")
    return {'message': 'AI test logs cleared'}


# ==================== PAYMENT SIMULATION PANEL ====================

@router.post('/payment/create')
async def create_test_payment(
    client_id: str,
    amount: float,
    payment_type: str = "cash-in",
    current_user: dict = Depends(get_current_admin)
):
    """
    Create a test payment for simulation.
    TEMPORARY - This is a mock panel to replace Telegram confirmation temporarily.
    """
    client = await fetch_one("SELECT * FROM clients WHERE client_id = $1", client_id)
    if not client:
        raise HTTPException(status_code=404, detail='Client not found')
    
    client = row_to_dict(client)
    
    order_id = generate_id()
    tx_id = generate_id()
    now = get_current_utc()
    
    # Determine transaction type
    if payment_type == "cash-in":
        order_type = "create"
        tx_type = "IN"
    elif payment_type == "cash-out":
        order_type = "redeem"
        tx_type = "OUT"
    else:
        raise HTTPException(status_code=400, detail='Invalid payment_type. Use cash-in or cash-out')
    
    # Create order
    await execute(
        """
        INSERT INTO orders (order_id, client_id, order_type, game, amount, status, created_at)
        VALUES ($1, $2, $3, 'Test Payment', $4, 'pending_confirmation', $5)
        """,
        order_id, client_id, order_type, amount, now
    )
    
    # Create pending transaction
    await execute(
        """
        INSERT INTO ledger_transactions (transaction_id, client_id, type, amount, wallet_type, status, source, order_id, reason, created_at)
        VALUES ($1, $2, $3, $4, 'real', 'pending', 'test_panel', $5, $6, $7)
        """,
        tx_id, client_id, tx_type, amount, order_id, f"Test {payment_type} via panel", now
    )
    
    return {
        'order_id': order_id,
        'transaction_id': tx_id,
        'client_id': client_id,
        'client_name': client.get('display_name', 'Unknown'),
        'amount': amount,
        'type': payment_type,
        'status': 'pending_confirmation',
        'message': 'Test payment created. Use /verify to mark as received.'
    }


@router.post('/payment/verify/{order_id}')
async def verify_test_payment(
    order_id: str,
    action: str = "received",
    adjusted_amount: Optional[float] = None,
    current_user: dict = Depends(get_current_admin)
):
    """
    Verify a test payment (mark as received, failed, or adjust amount).
    TEMPORARY - Simulates Telegram confirmation flow.
    """
    from utils import process_referral_on_deposit
    from database import get_pool
    pool = await get_pool()
    
    order = await fetch_one("SELECT * FROM orders WHERE order_id = $1", order_id)
    if not order:
        raise HTTPException(status_code=404, detail='Order not found')
    
    order = row_to_dict(order)
    
    if order['status'] not in ['pending_confirmation', 'pending_payout', 'pending_screenshot']:
        raise HTTPException(status_code=400, detail='Order already processed')
    
    now = get_current_utc()
    final_amount = adjusted_amount if adjusted_amount is not None else order['amount']
    
    if action == "received":
        # Mark as confirmed
        await execute(
            "UPDATE orders SET status = 'confirmed', amount = $1, confirmed_at = $2, confirmed_by = $3 WHERE order_id = $4",
            final_amount, now, current_user['id'], order_id
        )
        await execute(
            "UPDATE ledger_transactions SET status = 'confirmed', amount = $1, confirmed_at = $2, confirmed_by = $3 WHERE order_id = $4",
            final_amount, now, current_user['id'], order_id
        )
        
        # Process referral on deposit if it's a cash-in
        if order['order_type'] == 'create':
            await process_referral_on_deposit(pool, order['client_id'], final_amount)
        
        return {
            'order_id': order_id,
            'status': 'confirmed',
            'amount': final_amount,
            'message': 'Payment marked as received and confirmed'
        }
    
    elif action == "failed":
        await execute(
            "UPDATE orders SET status = 'rejected', rejection_reason = 'Payment failed/not received', confirmed_at = $1, confirmed_by = $2 WHERE order_id = $3",
            now, current_user['id'], order_id
        )
        await execute(
            "UPDATE ledger_transactions SET status = 'rejected', confirmed_at = $1, confirmed_by = $2 WHERE order_id = $3",
            now, current_user['id'], order_id
        )
        
        return {
            'order_id': order_id,
            'status': 'rejected',
            'message': 'Payment marked as failed'
        }
    
    else:
        raise HTTPException(status_code=400, detail='Invalid action. Use: received, failed')


@router.get('/payment/pending')
async def get_pending_test_payments(current_user: dict = Depends(get_current_admin)):
    """Get all pending test payments for the simulation panel."""
    orders = await fetch_all(
        """
        SELECT o.*, c.display_name as client_name 
        FROM orders o
        LEFT JOIN clients c ON o.client_id = c.client_id
        WHERE o.status IN ('pending_confirmation', 'pending_payout', 'pending_screenshot')
        ORDER BY o.created_at DESC
        LIMIT 100
        """
    )
    
    result = []
    for o in rows_to_list(orders):
        if o.get('created_at'):
            o['created_at'] = o['created_at'].isoformat()
        if o.get('confirmed_at'):
            o['confirmed_at'] = o['confirmed_at'].isoformat()
        result.append(o)
    
    return {'pending_payments': result}


@router.get('/payment/stats')
async def get_test_payment_stats(current_user: dict = Depends(get_current_admin)):
    """Get test payment statistics."""
    total_pending = (await fetch_one(
        "SELECT COUNT(*) as count FROM orders WHERE status IN ('pending_confirmation', 'pending_payout')"
    ))['count']
    
    total_confirmed = (await fetch_one(
        "SELECT COUNT(*) as count FROM orders WHERE status = 'confirmed'"
    ))['count']
    
    total_rejected = (await fetch_one(
        "SELECT COUNT(*) as count FROM orders WHERE status = 'rejected'"
    ))['count']
    
    total_in = await fetch_one(
        "SELECT COALESCE(SUM(amount), 0) as total FROM ledger_transactions WHERE type = 'IN' AND status = 'confirmed'"
    )
    
    total_out = await fetch_one(
        "SELECT COALESCE(SUM(amount), 0) as total FROM ledger_transactions WHERE type = 'OUT' AND status = 'confirmed'"
    )
    
    return {
        'pending_count': total_pending,
        'confirmed_count': total_confirmed,
        'rejected_count': total_rejected,
        'total_cash_in': total_in['total'] if total_in else 0,
        'total_cash_out': total_out['total'] if total_out else 0,
        'net_flow': (total_in['total'] if total_in else 0) - (total_out['total'] if total_out else 0)
    }


# ==================== TEST CLIENT CREATION ====================

@router.post('/clients/create-test')
async def create_test_client(
    display_name: str = "Test Player",
    with_balance: float = 0,
    current_user: dict = Depends(get_current_admin)
):
    """
    Create a test client for simulation purposes.
    TEMPORARY - For testing the payment panel without real clients.
    """
    client_id = generate_id()
    referral_code = generate_referral_code()
    
    # Ensure unique referral code
    while await fetch_one("SELECT client_id FROM clients WHERE referral_code = $1", referral_code):
        referral_code = generate_referral_code()
    
    now = get_current_utc()
    
    await execute(
        """
        INSERT INTO clients (client_id, display_name, referral_code, status, created_at)
        VALUES ($1, $2, $3, 'active', $4)
        """,
        client_id, display_name, referral_code, now
    )
    
    # Add initial balance if specified
    if with_balance > 0:
        tx_id = generate_id()
        await execute(
            """
            INSERT INTO ledger_transactions (transaction_id, client_id, type, amount, wallet_type, status, source, reason, created_at, confirmed_at)
            VALUES ($1, $2, 'IN', $3, 'real', 'confirmed', 'test_panel', 'Initial test balance', $4, $4)
            """,
            tx_id, client_id, with_balance, now
        )
    
    return {
        'client_id': client_id,
        'display_name': display_name,
        'referral_code': referral_code,
        'initial_balance': with_balance,
        'message': 'Test client created successfully'
    }
