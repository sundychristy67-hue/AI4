"""
Telegram Bot Admin Routes
Configure Telegram bot and send test notifications.
"""

from fastapi import APIRouter, HTTPException, status, Depends, Body
from typing import Optional
from pydantic import BaseModel
from auth import get_current_admin
from database import get_database
from utils import get_current_utc_iso, invalidate_settings_cache
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/telegram-admin', tags=['Telegram Admin'])


class TelegramSetupRequest(BaseModel):
    admin_chat_id: str


class SendTestMessageRequest(BaseModel):
    chat_id: str
    message: str


class SendNotificationRequest(BaseModel):
    notification_type: str  # 'deposit', 'withdrawal', 'custom'
    client_name: Optional[str] = "Test Client"
    amount: Optional[float] = 100.00
    order_id: Optional[str] = "test-order-123"
    custom_message: Optional[str] = None


@router.get('/status')
async def get_telegram_bot_status(current_user: dict = Depends(get_current_admin)):
    """Get Telegram bot connection status and configuration."""
    from services.telegram_service import test_bot_connection, TELEGRAM_ADMIN_CHAT_ID
    
    bot_status = await test_bot_connection()
    
    db = await get_database()
    settings = await db.global_settings.find_one({'_id': 'global'}, {'_id': 0})
    saved_chat_id = settings.get('telegram_admin_chat_id') if settings else None
    
    return {
        "bot_configured": bot_status.get('success', False),
        "bot_info": bot_status if bot_status.get('success') else None,
        "error": bot_status.get('error') if not bot_status.get('success') else None,
        "admin_chat_id_env": TELEGRAM_ADMIN_CHAT_ID or None,
        "admin_chat_id_db": saved_chat_id,
        "ready_to_send": bot_status.get('success') and (TELEGRAM_ADMIN_CHAT_ID or saved_chat_id)
    }


@router.post('/setup')
async def setup_telegram_admin(
    request: TelegramSetupRequest,
    current_user: dict = Depends(get_current_admin)
):
    """
    Save the Telegram admin chat ID for receiving notifications.
    
    To get your chat ID:
    1. Message your bot on Telegram
    2. The bot will tell you your chat ID
    Or use @userinfobot on Telegram
    """
    db = await get_database()
    
    # Save to global settings
    await db.global_settings.update_one(
        {'_id': 'global'},
        {
            '$set': {
                'telegram_admin_chat_id': request.admin_chat_id,
                'telegram_setup_by': current_user['id'],
                'telegram_setup_at': get_current_utc_iso()
            }
        },
        upsert=True
    )
    
    # Also update environment variable for current session
    os.environ['TELEGRAM_ADMIN_CHAT_ID'] = request.admin_chat_id
    
    invalidate_settings_cache()
    
    # Send test message
    from services.telegram_service import send_message
    test_result = await send_message(
        request.admin_chat_id,
        "✅ <b>Telegram Bot Connected!</b>\n\n"
        "You will now receive payment notifications here.\n\n"
        "Available commands:\n"
        "/pending - View pending orders\n"
        "/help - Show help"
    )
    
    return {
        "success": True,
        "message": "Telegram admin chat configured",
        "chat_id": request.admin_chat_id,
        "test_message_sent": test_result
    }


@router.post('/test-message')
async def send_test_message(
    request: SendTestMessageRequest,
    current_user: dict = Depends(get_current_admin)
):
    """Send a test message to verify bot is working."""
    from services.telegram_service import send_message
    
    result = await send_message(request.chat_id, request.message)
    
    return {
        "success": result,
        "message": "Message sent" if result else "Failed to send message"
    }


@router.post('/send-notification')
async def send_notification(
    request: SendNotificationRequest,
    current_user: dict = Depends(get_current_admin)
):
    """Send a test notification to admin chat."""
    from services.telegram_service import (
        notify_new_deposit, 
        notify_new_withdrawal,
        send_admin_notification,
        TELEGRAM_ADMIN_CHAT_ID
    )
    
    db = await get_database()
    settings = await db.global_settings.find_one({'_id': 'global'}, {'_id': 0})
    chat_id = settings.get('telegram_admin_chat_id') if settings else TELEGRAM_ADMIN_CHAT_ID
    
    if not chat_id:
        raise HTTPException(
            status_code=400, 
            detail="Admin chat ID not configured. Use /setup first."
        )
    
    result = False
    
    if request.notification_type == 'deposit':
        result = await notify_new_deposit(
            order_id=request.order_id or "test-order-123",
            client_name=request.client_name or "Test Client",
            amount=request.amount or 100.00,
            payment_method="GCash",
            reference="TEST-REF-001",
            admin_chat_id=chat_id
        )
    elif request.notification_type == 'withdrawal':
        result = await notify_new_withdrawal(
            order_id=request.order_id or "test-order-456",
            client_name=request.client_name or "Test Client",
            amount=request.amount or 50.00,
            payout_method="GCash",
            payout_details="09171234567",
            admin_chat_id=chat_id
        )
    elif request.notification_type == 'custom' and request.custom_message:
        result = await send_admin_notification(request.custom_message)
    else:
        raise HTTPException(status_code=400, detail="Invalid notification type")
    
    return {
        "success": result,
        "notification_type": request.notification_type,
        "message": "Notification sent" if result else "Failed to send notification"
    }


@router.get('/pending-orders')
async def get_pending_orders_for_telegram(current_user: dict = Depends(get_current_admin)):
    """Get pending orders and optionally send to Telegram."""
    db = await get_database()
    
    orders = await db.orders.find(
        {'status': {'$in': ['pending_confirmation', 'pending_screenshot', 'pending_payout']}},
        {'_id': 0}
    ).sort('created_at', -1).to_list(50)
    
    # Enrich with client names
    client_ids = list(set([o['client_id'] for o in orders]))
    clients = await db.clients.find(
        {'client_id': {'$in': client_ids}},
        {'_id': 0, 'client_id': 1, 'display_name': 1}
    ).to_list(100)
    clients_map = {c['client_id']: c.get('display_name', 'Unknown') for c in clients}
    
    enriched = []
    for order in orders:
        enriched.append({
            **order,
            'client_name': clients_map.get(order['client_id'], 'Unknown')
        })
    
    return {
        "count": len(enriched),
        "orders": enriched
    }


@router.post('/send-pending-summary')
async def send_pending_summary_to_telegram(current_user: dict = Depends(get_current_admin)):
    """Send pending orders summary to Telegram admin chat."""
    from services.telegram_service import send_pending_orders_list
    
    db = await get_database()
    settings = await db.global_settings.find_one({'_id': 'global'}, {'_id': 0})
    chat_id = settings.get('telegram_admin_chat_id') if settings else None
    
    if not chat_id:
        chat_id = os.environ.get('TELEGRAM_ADMIN_CHAT_ID')
    
    if not chat_id:
        raise HTTPException(status_code=400, detail="Admin chat ID not configured")
    
    # Get pending orders
    orders = await db.orders.find(
        {'status': {'$in': ['pending_confirmation', 'pending_screenshot', 'pending_payout']}},
        {'_id': 0}
    ).sort('created_at', -1).to_list(50)
    
    # Enrich with client names
    client_ids = list(set([o['client_id'] for o in orders]))
    clients = await db.clients.find(
        {'client_id': {'$in': client_ids}},
        {'_id': 0, 'client_id': 1, 'display_name': 1}
    ).to_list(100)
    clients_map = {c['client_id']: c.get('display_name', 'Unknown') for c in clients}
    
    enriched = []
    for order in orders:
        enriched.append({
            **order,
            'client_name': clients_map.get(order['client_id'], 'Unknown')
        })
    
    result = await send_pending_orders_list(enriched, chat_id)
    
    return {
        "success": result,
        "orders_count": len(enriched),
        "message": "Summary sent to Telegram" if result else "Failed to send"
    }


# ==================== WEBHOOK FOR BOT CALLBACKS ====================

@router.post('/webhook')
async def telegram_webhook(update: dict = Body(...)):
    """
    Handle incoming Telegram webhook updates.
    This processes callback queries from inline keyboard buttons.
    """
    from services.telegram_service import send_message, bot
    from telegram import Update as TelegramUpdate
    
    logger.info(f"Received Telegram webhook: {update}")
    
    # Handle callback queries (button clicks)
    if 'callback_query' in update:
        callback = update['callback_query']
        callback_data = callback.get('data', '')
        chat_id = callback['message']['chat']['id']
        message_id = callback['message']['message_id']
        user = callback.get('from', {})
        
        logger.info(f"Callback: {callback_data} from {user.get('username', 'unknown')}")
        
        # Parse callback data
        if callback_data.startswith('confirm_'):
            order_id = callback_data.replace('confirm_', '')
            # Process confirmation
            result = await process_order_action(order_id, 'confirm', user.get('username', 'telegram_admin'))
            await send_message(chat_id, result['message'])
            
        elif callback_data.startswith('reject_'):
            order_id = callback_data.replace('reject_', '')
            # Ask for rejection reason
            await send_message(
                chat_id, 
                f"To reject order <code>{order_id[:16]}...</code>\n\n"
                f"Reply with: /reject {order_id[:16]} [reason]\n\n"
                f"Example: /reject {order_id[:16]} Payment not received"
            )
            
        elif callback_data.startswith('edit_'):
            order_id = callback_data.replace('edit_', '')
            # Ask for new amount
            await send_message(
                chat_id,
                f"To edit order <code>{order_id[:16]}...</code>\n\n"
                f"Reply with: /edit {order_id[:16]} [new_amount] [reason]\n\n"
                f"Example: /edit {order_id[:16]} 95.00 Mismatch - actual amount received"
            )
        
        # Answer callback query to remove loading state
        if bot:
            try:
                await bot.answer_callback_query(callback['id'])
            except Exception as e:
                logger.error(f"Failed to answer callback: {e}")
    
    # Handle text commands
    elif 'message' in update and 'text' in update['message']:
        message = update['message']
        text = message['text']
        chat_id = message['chat']['id']
        user = message.get('from', {})
        
        if text.startswith('/start'):
            await send_message(
                chat_id,
                "👋 <b>Welcome to Payment Bot!</b>\n\n"
                f"Your Chat ID: <code>{chat_id}</code>\n\n"
                "Save this Chat ID in the admin panel to receive payment notifications.\n\n"
                "Commands:\n"
                "/pending - View pending orders\n"
                "/help - Show help"
            )
            
        elif text.startswith('/pending'):
            db = await get_database()
            orders = await db.orders.find(
                {'status': {'$in': ['pending_confirmation', 'pending_screenshot']}},
                {'_id': 0}
            ).to_list(20)
            
            if not orders:
                await send_message(chat_id, "✅ No pending orders!")
            else:
                msg = f"📋 <b>Pending Orders ({len(orders)})</b>\n\n"
                for o in orders[:10]:
                    emoji = "💰" if o.get('order_type') == 'create' else "🏧"
                    msg += f"{emoji} ${o.get('amount', 0):.2f} - <code>{o.get('order_id', '')[:12]}...</code>\n"
                await send_message(chat_id, msg)
                
        elif text.startswith('/confirm '):
            parts = text.split(' ', 1)
            if len(parts) >= 2:
                order_id_partial = parts[1].strip()
                result = await find_and_process_order(order_id_partial, 'confirm', user.get('username'))
                await send_message(chat_id, result['message'])
                
        elif text.startswith('/reject '):
            parts = text.split(' ', 2)
            if len(parts) >= 3:
                order_id_partial = parts[1].strip()
                reason = parts[2].strip()
                result = await find_and_process_order(order_id_partial, 'reject', user.get('username'), reason=reason)
                await send_message(chat_id, result['message'])
            else:
                await send_message(chat_id, "Usage: /reject [order_id] [reason]")
                
        elif text.startswith('/edit '):
            parts = text.split(' ', 3)
            if len(parts) >= 4:
                order_id_partial = parts[1].strip()
                try:
                    new_amount = float(parts[2])
                    reason = parts[3].strip()
                    result = await find_and_process_order(
                        order_id_partial, 'edit', user.get('username'),
                        new_amount=new_amount, reason=reason
                    )
                    await send_message(chat_id, result['message'])
                except ValueError:
                    await send_message(chat_id, "Invalid amount. Usage: /edit [order_id] [amount] [reason]")
            else:
                await send_message(chat_id, "Usage: /edit [order_id] [new_amount] [reason]")
                
        elif text.startswith('/help'):
            await send_message(
                chat_id,
                "<b>📖 Bot Commands</b>\n\n"
                "/pending - View pending orders\n"
                "/confirm [order_id] - Confirm an order\n"
                "/reject [order_id] [reason] - Reject an order\n"
                "/edit [order_id] [amount] [reason] - Edit amount\n"
                "/help - Show this help\n\n"
                "<i>You can also use the inline buttons on order notifications.</i>"
            )
    
    return {"ok": True}


async def find_and_process_order(order_id_partial: str, action: str, admin: str, **kwargs):
    """Find order by partial ID and process action."""
    db = await get_database()
    
    # Find order by partial ID
    order = await db.orders.find_one(
        {'order_id': {'$regex': f'^{order_id_partial}'}},
        {'_id': 0}
    )
    
    if not order:
        return {"success": False, "message": f"❌ Order not found: {order_id_partial}"}
    
    return await process_order_action(order['order_id'], action, admin, **kwargs)


async def process_order_action(order_id: str, action: str, admin: str, **kwargs):
    """Process an order action (confirm/reject/edit)."""
    db = await get_database()
    from utils import calculate_wallet_balances, process_referral_on_deposit
    
    order = await db.orders.find_one({'order_id': order_id}, {'_id': 0})
    if not order:
        return {"success": False, "message": f"❌ Order not found"}
    
    if order['status'] not in ['pending_confirmation', 'pending_screenshot', 'pending_payout']:
        return {"success": False, "message": f"❌ Order already processed (status: {order['status']})"}
    
    client = await db.clients.find_one({'client_id': order['client_id']}, {'_id': 0})
    client_name = client.get('display_name', 'Unknown') if client else 'Unknown'
    now = get_current_utc_iso()
    
    if action == 'confirm':
        # Update order
        await db.orders.update_one(
            {'order_id': order_id},
            {'$set': {'status': 'confirmed', 'confirmed_at': now, 'confirmed_by': admin}}
        )
        
        # Update transaction
        await db.ledger_transactions.update_one(
            {'order_id': order_id},
            {'$set': {'status': 'confirmed', 'confirmed_at': now}}
        )
        
        # Process referral if deposit
        if order.get('order_type') == 'create':
            await process_referral_on_deposit(db, order['client_id'], order['amount'])
        
        # Get new balance
        wallet = await calculate_wallet_balances(db, order['client_id'])
        
        return {
            "success": True,
            "message": f"✅ <b>Order Confirmed!</b>\n\n"
                      f"Client: {client_name}\n"
                      f"Amount: ${order['amount']:.2f}\n"
                      f"New Balance: ${wallet['real_balance']:.2f}"
        }
        
    elif action == 'reject':
        reason = kwargs.get('reason', 'Rejected by admin')
        
        await db.orders.update_one(
            {'order_id': order_id},
            {'$set': {'status': 'rejected', 'rejection_reason': reason, 'confirmed_at': now, 'confirmed_by': admin}}
        )
        
        await db.ledger_transactions.update_one(
            {'order_id': order_id},
            {'$set': {'status': 'rejected', 'confirmed_at': now}}
        )
        
        return {
            "success": True,
            "message": f"❌ <b>Order Rejected</b>\n\n"
                      f"Client: {client_name}\n"
                      f"Amount: ${order['amount']:.2f}\n"
                      f"Reason: {reason}"
        }
        
    elif action == 'edit':
        new_amount = kwargs.get('new_amount')
        reason = kwargs.get('reason', 'Amount adjusted')
        
        if not new_amount:
            return {"success": False, "message": "❌ New amount required for edit"}
        
        original = order.get('original_amount') or order['amount']
        
        await db.orders.update_one(
            {'order_id': order_id},
            {'$set': {
                'amount': new_amount,
                'original_amount': original,
                'amount_edited_by': admin,
                'amount_edit_reason': reason
            }}
        )
        
        await db.ledger_transactions.update_one(
            {'order_id': order_id},
            {'$set': {'amount': new_amount, 'original_amount': original}}
        )
        
        return {
            "success": True,
            "message": f"✏️ <b>Amount Edited</b>\n\n"
                      f"Client: {client_name}\n"
                      f"Original: ${original:.2f}\n"
                      f"New Amount: ${new_amount:.2f}\n"
                      f"Reason: {reason}\n\n"
                      f"<i>Use /confirm {order_id[:12]} to confirm</i>"
        }
    
    return {"success": False, "message": "❌ Unknown action"}
