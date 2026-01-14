"""
Test Routes - AI Test Spot & Payment Simulation Panel
TEMPORARY IMPLEMENTATION FOR TESTING

These routes provide:
1. AI Test Spot - Isolated area for testing AI conversations (NOW WITH REAL GPT!)
2. Payment Simulation - Manual payment verification without Telegram/Chatwoot
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel
from models import OrderStatus, TransactionStatus, TransactionType, WalletType
from auth import get_current_admin
from database import get_database
from utils import generate_id, get_current_utc_iso, calculate_wallet_balances, process_referral_on_deposit
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/test', tags=['Test Mode'])

# Initialize GPT Chat
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

GAMING_SYSTEM_PROMPT = """You are a helpful AI assistant for a gaming platform. You help users with:

1. **Account & Balance Questions**: Explain how to check balances (Real wallet + Bonus wallet)
2. **Loading Credits**: Guide users to load credits to their favorite games
3. **Withdrawals**: Explain withdrawal process and minimum requirements ($20 minimum)
4. **Referral Program**: Explain how referrals work (5-10% commission based on tier)
5. **Game Information**: Help users find games, download links, and availability
6. **Technical Support**: Basic troubleshooting for common issues

**Important Rules:**
- Be friendly and helpful
- Keep responses concise but informative
- For sensitive actions (payments, withdrawals), remind users to use the official portal
- Never share actual credentials or sensitive data
- If unsure, recommend contacting support via Messenger

**Platform Features:**
- Games catalog with availability status (Available, Maintenance, Unavailable)
- Real wallet (withdrawable) and Bonus wallet (non-withdrawable, for games only)
- Referral program with tiered commissions
- Secure portal access via magic link or password"""


# ==================== MODELS ====================

class PaymentSimulateRequest(BaseModel):
    """Simulate a payment creation (like from Telegram)"""
    client_id: str
    amount: float
    payment_type: str  # 'cashin' or 'cashout'
    payment_method: Optional[str] = "GCash"
    notes: Optional[str] = None


class PaymentActionRequest(BaseModel):
    """Mark payment as received/failed or adjust amount"""
    order_id: str
    action: str  # 'received', 'failed', 'adjust'
    new_amount: Optional[float] = None
    reason: Optional[str] = None


class AITestMessage(BaseModel):
    """AI Test conversation message"""
    role: str  # 'user' or 'assistant'
    content: str


class AITestConversation(BaseModel):
    """AI Test conversation request"""
    messages: List[AITestMessage]
    test_scenario: Optional[str] = None  # 'client_query', 'agent_response', 'admin_action'


# ==================== AI TEST SPOT ====================

@router.get('/ai-test/info')
async def get_ai_test_info(current_user: dict = Depends(get_current_admin)):
    """Get AI Test Spot information and available scenarios."""
    return {
        "test_mode": False,
        "ai_enabled": True,
        "model": "GPT-4o (OpenAI)",
        "warning": "LIVE AI - Real GPT responses. No real payments or automation triggers.",
        "available_scenarios": [
            {
                "id": "client_query",
                "name": "Client Query Simulation",
                "description": "Test how AI responds to client questions about the platform"
            },
            {
                "id": "agent_response",
                "name": "Agent Response Testing",
                "description": "Test agent responses to various support scenarios"
            },
            {
                "id": "payment_flow",
                "name": "Payment Flow Testing",
                "description": "Test payment-related queries and guidance"
            },
            {
                "id": "error_handling",
                "name": "Error Handling",
                "description": "Test error responses and edge cases"
            }
        ],
        "sample_prompts": {
            "client_query": [
                "How do I load credits to my game?",
                "What is my current balance?",
                "How do referrals work?",
                "I want to withdraw my earnings"
            ],
            "agent_response": [
                "User requesting cash-in of $100",
                "User reporting incorrect balance",
                "User asking about failed transaction"
            ],
            "payment_flow": [
                "How do I make a deposit?",
                "What payment methods do you accept?",
                "My payment is pending, what should I do?"
            ],
            "error_handling": [
                "I can't login to my account",
                "The game is not loading",
                "I didn't receive my bonus"
            ]
        }
    }


@router.post('/ai-test/simulate')
async def simulate_ai_conversation(
    conversation: AITestConversation,
    current_user: dict = Depends(get_current_admin)
):
    """
    Chat with real GPT AI for testing purposes.
    Uses OpenAI GPT-4o via Emergent integrations.
    """
    db = await get_database()
    
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="AI not configured - EMERGENT_LLM_KEY not found")
    
    # Generate session ID for this conversation
    session_id = f"ai_test_{current_user['id']}_{generate_id()[:8]}"
    
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        # Initialize the chat with GPT-4o
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=GAMING_SYSTEM_PROMPT
        ).with_model("openai", "gpt-4o")
        
        # Get the last user message
        last_message = conversation.messages[-1].content if conversation.messages else ""
        
        # Add context from scenario
        scenario_context = ""
        if conversation.test_scenario == "client_query":
            scenario_context = "[Context: This is a client asking about the gaming platform] "
        elif conversation.test_scenario == "agent_response":
            scenario_context = "[Context: You are helping an agent respond to a user scenario] "
        elif conversation.test_scenario == "payment_flow":
            scenario_context = "[Context: User has payment-related questions] "
        elif conversation.test_scenario == "error_handling":
            scenario_context = "[Context: User is experiencing an issue] "
        
        # Send message to GPT
        user_message = UserMessage(text=scenario_context + last_message)
        response_text = await chat.send_message(user_message)
        
        # Log the test
        test_log = {
            "id": generate_id(),
            "admin_id": current_user['id'],
            "scenario": conversation.test_scenario,
            "messages": [m.dict() for m in conversation.messages],
            "ai_response": response_text,
            "timestamp": get_current_utc_iso(),
            "mode": "LIVE_GPT",
            "model": "gpt-4o"
        }
        await db.ai_test_logs.insert_one(test_log)
        
        return {
            "test_mode": False,
            "ai_enabled": True,
            "response": {
                "role": "assistant",
                "content": response_text
            },
            "test_id": test_log["id"],
            "model": "GPT-4o (OpenAI)",
            "info": "Real AI response from GPT-4o"
        }
        
    except Exception as e:
        logger.error(f"AI chat error: {str(e)}")
        
        # Log the error
        error_log = {
            "id": generate_id(),
            "admin_id": current_user['id'],
            "scenario": conversation.test_scenario,
            "messages": [m.dict() for m in conversation.messages],
            "error": str(e),
            "timestamp": get_current_utc_iso(),
            "mode": "ERROR"
        }
        await db.ai_test_logs.insert_one(error_log)
        
        raise HTTPException(
            status_code=500, 
            detail=f"AI error: {str(e)}"
        )


@router.get('/ai-test/logs')
async def get_ai_test_logs(
    limit: int = 50,
    current_user: dict = Depends(get_current_admin)
):
    """Get AI test conversation logs."""
    db = await get_database()
    
    logs = await db.ai_test_logs.find(
        {},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return {"logs": logs, "test_mode": True}


# ==================== PAYMENT SIMULATION PANEL ====================

@router.post('/payment/simulate')
async def simulate_payment(
    request: PaymentSimulateRequest,
    current_user: dict = Depends(get_current_admin)
):
    """
    TEMPORARY: Simulate a payment creation (replaces Telegram bot triggers).
    Creates a test order that can be manually verified.
    """
    db = await get_database()
    
    # Verify client exists
    client = await db.clients.find_one({"client_id": request.client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    order_id = generate_id()
    tx_id = generate_id()
    
    # Determine transaction type
    if request.payment_type == "cashin":
        tx_type = TransactionType.IN.value
        order_type = "create"  # Load/recharge
    else:
        tx_type = TransactionType.OUT.value
        order_type = "redeem"  # Withdrawal
    
    # Create test order
    order_doc = {
        "order_id": order_id,
        "client_id": request.client_id,
        "order_type": order_type,
        "game": "Test Payment",
        "amount": request.amount,
        "wallet_type": WalletType.REAL.value,
        "payment_method": request.payment_method,
        "status": OrderStatus.PENDING_CONFIRMATION.value,
        "created_at": get_current_utc_iso(),
        "test_mode": True,
        "notes": request.notes,
        "created_by": current_user['id']
    }
    await db.orders.insert_one(order_doc)
    
    # Create pending transaction
    tx_doc = {
        "transaction_id": tx_id,
        "client_id": request.client_id,
        "type": tx_type,
        "amount": request.amount,
        "wallet_type": WalletType.REAL.value,
        "status": TransactionStatus.PENDING.value,
        "source": "test_simulation",
        "order_id": order_id,
        "reason": f"Test {request.payment_type} simulation",
        "created_at": get_current_utc_iso(),
        "test_mode": True
    }
    await db.ledger_transactions.insert_one(tx_doc)
    
    # Log the action
    await db.audit_logs.insert_one({
        "id": generate_id(),
        "admin_id": current_user['id'],
        "action": "test_payment_simulate",
        "entity_type": "order",
        "entity_id": order_id,
        "details": {
            "client_id": request.client_id,
            "amount": request.amount,
            "payment_type": request.payment_type,
            "test_mode": True
        },
        "timestamp": get_current_utc_iso()
    })
    
    return {
        "success": True,
        "test_mode": True,
        "message": f"Test {request.payment_type} created. Use payment panel to mark as received/failed.",
        "order_id": order_id,
        "transaction_id": tx_id,
        "client_name": client.get("display_name", "Unknown"),
        "amount": request.amount,
        "status": "pending_confirmation",
        "warning": "TEMPORARY - This simulates what Telegram bot would create"
    }


@router.get('/payment/pending')
async def get_pending_payments(
    test_only: bool = False,
    current_user: dict = Depends(get_current_admin)
):
    """Get all pending payment orders for verification."""
    db = await get_database()
    
    query = {
        "status": {"$in": [
            OrderStatus.PENDING_CONFIRMATION.value,
            OrderStatus.PENDING_SCREENSHOT.value,
            OrderStatus.PENDING_PAYOUT.value
        ]}
    }
    
    if test_only:
        query["test_mode"] = True
    
    orders = await db.orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    
    # Enrich with client info
    client_ids = list(set([o["client_id"] for o in orders]))
    clients = await db.clients.find(
        {"client_id": {"$in": client_ids}},
        {"_id": 0, "client_id": 1, "display_name": 1}
    ).to_list(200)
    clients_map = {c["client_id"]: c for c in clients}
    
    enriched_orders = []
    for order in orders:
        client = clients_map.get(order["client_id"], {})
        enriched_orders.append({
            **order,
            "client_name": client.get("display_name", "Unknown"),
            "is_test": order.get("test_mode", False)
        })
    
    return {
        "orders": enriched_orders,
        "total": len(enriched_orders),
        "test_mode_indicator": "Orders marked with is_test=true are simulated"
    }


@router.post('/payment/action')
async def process_payment_action(
    request: PaymentActionRequest,
    current_user: dict = Depends(get_current_admin)
):
    """
    TEMPORARY: Process payment action (mark received/failed/adjust).
    Replaces Telegram inline keyboard functionality.
    """
    db = await get_database()
    
    # Get order
    order = await db.orders.find_one({"order_id": request.order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order["status"] not in [
        OrderStatus.PENDING_CONFIRMATION.value,
        OrderStatus.PENDING_SCREENSHOT.value,
        OrderStatus.PENDING_PAYOUT.value
    ]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot process order in status: {order['status']}"
        )
    
    now = get_current_utc_iso()
    
    if request.action == "received":
        # Mark as confirmed/received
        new_status = OrderStatus.CONFIRMED.value
        tx_status = TransactionStatus.CONFIRMED.value
        message = "Payment marked as RECEIVED"
        
        # Update order
        await db.orders.update_one(
            {"order_id": request.order_id},
            {"$set": {
                "status": new_status,
                "confirmed_at": now,
                "confirmed_by": current_user['id']
            }}
        )
        
        # Update transaction
        await db.ledger_transactions.update_one(
            {"order_id": request.order_id},
            {"$set": {
                "status": tx_status,
                "confirmed_at": now,
                "confirmed_by": current_user['id']
            }}
        )
        
        # Process referral for cash-in (deposit)
        if order.get("order_type") == "create":
            # Get final amount (may have been adjusted)
            final_order = await db.orders.find_one({"order_id": request.order_id}, {"_id": 0})
            amount = final_order.get("amount", order["amount"])
            await process_referral_on_deposit(db, order["client_id"], amount)
        
    elif request.action == "failed":
        # Mark as rejected/failed
        new_status = OrderStatus.REJECTED.value
        tx_status = TransactionStatus.REJECTED.value
        message = f"Payment marked as FAILED. Reason: {request.reason or 'Not specified'}"
        
        await db.orders.update_one(
            {"order_id": request.order_id},
            {"$set": {
                "status": new_status,
                "rejection_reason": request.reason or "Payment verification failed",
                "confirmed_at": now,
                "confirmed_by": current_user['id']
            }}
        )
        
        await db.ledger_transactions.update_one(
            {"order_id": request.order_id},
            {"$set": {
                "status": tx_status,
                "confirmed_at": now,
                "confirmed_by": current_user['id']
            }}
        )
        
    elif request.action == "adjust":
        # Adjust amount (for mismatch testing)
        if request.new_amount is None:
            raise HTTPException(status_code=400, detail="new_amount required for adjust action")
        
        original_amount = order.get("original_amount") or order["amount"]
        
        await db.orders.update_one(
            {"order_id": request.order_id},
            {"$set": {
                "amount": request.new_amount,
                "original_amount": original_amount,
                "amount_adjusted_by": current_user['id'],
                "adjustment_reason": request.reason
            }}
        )
        
        await db.ledger_transactions.update_one(
            {"order_id": request.order_id},
            {"$set": {
                "amount": request.new_amount,
                "original_amount": original_amount
            }}
        )
        
        message = f"Amount adjusted from ${original_amount:.2f} to ${request.new_amount:.2f}"
        
    else:
        raise HTTPException(status_code=400, detail=f"Invalid action: {request.action}")
    
    # Log action
    await db.audit_logs.insert_one({
        "id": generate_id(),
        "admin_id": current_user['id'],
        "action": f"test_payment_{request.action}",
        "entity_type": "order",
        "entity_id": request.order_id,
        "details": {
            "action": request.action,
            "new_amount": request.new_amount,
            "reason": request.reason,
            "test_mode": order.get("test_mode", False)
        },
        "timestamp": now
    })
    
    # Get updated wallet balance
    wallet = await calculate_wallet_balances(db, order["client_id"])
    
    return {
        "success": True,
        "message": message,
        "order_id": request.order_id,
        "action": request.action,
        "new_wallet_balance": {
            "real": wallet["real_balance"],
            "bonus": wallet["bonus_balance"]
        },
        "warning": "TEMPORARY - This replaces Telegram confirmation flow"
    }


@router.get('/payment/order/{order_id}')
async def get_payment_order_detail(
    order_id: str,
    current_user: dict = Depends(get_current_admin)
):
    """Get detailed information about a payment order."""
    db = await get_database()
    
    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get client info
    client = await db.clients.find_one(
        {"client_id": order["client_id"]},
        {"_id": 0}
    )
    
    # Get transaction
    transaction = await db.ledger_transactions.find_one(
        {"order_id": order_id},
        {"_id": 0}
    )
    
    # Get wallet balance
    wallet = await calculate_wallet_balances(db, order["client_id"])
    
    return {
        "order": order,
        "client": client,
        "transaction": transaction,
        "wallet": wallet,
        "is_test": order.get("test_mode", False),
        "available_actions": ["received", "failed", "adjust"] if order["status"] in [
            OrderStatus.PENDING_CONFIRMATION.value,
            OrderStatus.PENDING_SCREENSHOT.value,
            OrderStatus.PENDING_PAYOUT.value
        ] else []
    }


# ==================== TEST DATA MANAGEMENT ====================

@router.post('/data/create-test-client')
async def create_test_client(
    display_name: Optional[str] = "Test Client",
    current_user: dict = Depends(get_current_admin)
):
    """Create a test client for testing purposes."""
    db = await get_database()
    
    from utils import generate_referral_code
    
    client_id = generate_id()
    referral_code = generate_referral_code()
    
    client_doc = {
        "client_id": client_id,
        "chatwoot_contact_id": f"test_{client_id[:8]}",
        "messenger_psid": None,
        "display_name": display_name,
        "status": "active",
        "withdraw_locked": False,
        "load_locked": False,
        "bonus_locked": False,
        "referral_code": referral_code,
        "referred_by_code": None,
        "referral_locked": False,
        "referral_count": 0,
        "valid_referral_count": 0,
        "bonus_claims": 0,
        "visibility_level": "full",
        "created_at": get_current_utc_iso(),
        "last_active_at": get_current_utc_iso(),
        "test_mode": True
    }
    
    await db.clients.insert_one(client_doc)
    
    # Remove _id before returning
    client_doc.pop('_id', None)
    
    return {
        "success": True,
        "client": client_doc,
        "message": "Test client created successfully",
        "test_mode": True
    }


@router.get('/data/stats')
async def get_test_stats(current_user: dict = Depends(get_current_admin)):
    """Get test mode statistics."""
    db = await get_database()
    
    test_clients = await db.clients.count_documents({"test_mode": True})
    test_orders = await db.orders.count_documents({"test_mode": True})
    test_ai_logs = await db.ai_test_logs.count_documents({})
    
    pending_orders = await db.orders.count_documents({
        "status": {"$in": [
            OrderStatus.PENDING_CONFIRMATION.value,
            OrderStatus.PENDING_SCREENSHOT.value,
            OrderStatus.PENDING_PAYOUT.value
        ]}
    })
    
    return {
        "test_mode": True,
        "stats": {
            "test_clients": test_clients,
            "test_orders": test_orders,
            "ai_test_conversations": test_ai_logs,
            "pending_payments": pending_orders
        },
        "note": "TEMPORARY - Test mode statistics for development"
    }
