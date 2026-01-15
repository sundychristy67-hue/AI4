"""
Telegram Admin Routes - Admin configuration for Telegram bot
PostgreSQL Version
"""
from fastapi import APIRouter, HTTPException, status, Depends
from auth import get_current_admin
from database import fetch_one, execute, row_to_dict
from utils import get_current_utc, get_global_settings, invalidate_settings_cache
from config import settings
import json
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/telegram', tags=['Telegram Admin'])


@router.get('/config')
async def get_telegram_config(current_user: dict = Depends(get_current_admin)):
    """Get current Telegram bot configuration."""
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.environ.get('TELEGRAM_ADMIN_CHAT_ID', '')
    
    from database import get_pool
    pool = await get_pool()
    settings_data = await get_global_settings(pool)
    telegram_config = settings_data.get('telegram_config', {})
    
    return {
        'bot_token_configured': bool(bot_token),
        'bot_token_masked': f"{bot_token[:10]}...{bot_token[-5:]}" if len(bot_token) > 15 else "Not set",
        'admin_chat_id': chat_id or telegram_config.get('admin_chat_id', ''),
        'notifications_enabled': telegram_config.get('notifications_enabled', False),
        'notify_on_payment': telegram_config.get('notify_on_payment', True),
        'notify_on_withdrawal': telegram_config.get('notify_on_withdrawal', True),
        'notify_on_new_client': telegram_config.get('notify_on_new_client', False)
    }


@router.post('/setup')
async def setup_telegram(
    admin_chat_id: str,
    notifications_enabled: bool = True,
    notify_on_payment: bool = True,
    notify_on_withdrawal: bool = True,
    notify_on_new_client: bool = False,
    current_user: dict = Depends(get_current_admin)
):
    """Set up Telegram bot configuration."""
    telegram_config = {
        'admin_chat_id': admin_chat_id,
        'notifications_enabled': notifications_enabled,
        'notify_on_payment': notify_on_payment,
        'notify_on_withdrawal': notify_on_withdrawal,
        'notify_on_new_client': notify_on_new_client,
        'configured_by': current_user['id'],
        'configured_at': get_current_utc().isoformat()
    }
    
    # Ensure settings exist
    existing = await fetch_one("SELECT id FROM global_settings WHERE id = 'global'")
    if not existing:
        await execute(
            "INSERT INTO global_settings (id, telegram_config) VALUES ('global', $1)",
            json.dumps(telegram_config)
        )
    else:
        await execute(
            "UPDATE global_settings SET telegram_config = $1, updated_at = $2, updated_by = $3 WHERE id = 'global'",
            json.dumps(telegram_config), get_current_utc(), current_user['id']
        )
    
    invalidate_settings_cache()
    
    return {
        'success': True,
        'message': 'Telegram configuration saved',
        'config': telegram_config
    }


@router.post('/test-message')
async def send_test_message(current_user: dict = Depends(get_current_admin)):
    """Send a test message to verify Telegram setup."""
    from services.telegram_service import send_telegram_message
    
    from database import get_pool
    pool = await get_pool()
    settings_data = await get_global_settings(pool)
    telegram_config = settings_data.get('telegram_config', {})
    
    chat_id = telegram_config.get('admin_chat_id') or os.environ.get('TELEGRAM_ADMIN_CHAT_ID', '')
    
    if not chat_id:
        raise HTTPException(status_code=400, detail='Admin chat ID not configured')
    
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    if not bot_token:
        raise HTTPException(status_code=400, detail='Bot token not configured in environment')
    
    test_message = f"🔔 Test Message from Gaming Platform\n\nThis is a test notification sent by admin: {current_user.get('username', 'Unknown')}\n\nIf you received this message, your Telegram notifications are working correctly!"
    
    try:
        result = await send_telegram_message(chat_id, test_message)
        if result:
            return {'success': True, 'message': 'Test message sent successfully'}
        else:
            return {'success': False, 'message': 'Failed to send test message'}
    except Exception as e:
        logger.error(f"Failed to send test message: {e}")
        raise HTTPException(status_code=500, detail=f'Failed to send message: {str(e)}')


@router.post('/notify/payment')
async def notify_payment(
    order_id: str,
    client_name: str,
    amount: float,
    payment_type: str,
    current_user: dict = Depends(get_current_admin)
):
    """Send payment notification to admin Telegram."""
    from services.telegram_service import send_telegram_message
    
    from database import get_pool
    pool = await get_pool()
    settings_data = await get_global_settings(pool)
    telegram_config = settings_data.get('telegram_config', {})
    
    if not telegram_config.get('notifications_enabled'):
        return {'success': False, 'message': 'Notifications disabled'}
    
    if not telegram_config.get('notify_on_payment'):
        return {'success': False, 'message': 'Payment notifications disabled'}
    
    chat_id = telegram_config.get('admin_chat_id') or os.environ.get('TELEGRAM_ADMIN_CHAT_ID', '')
    if not chat_id:
        return {'success': False, 'message': 'Chat ID not configured'}
    
    emoji = "💰" if payment_type == "cash-in" else "💸"
    message = f"""{emoji} New {payment_type.upper()} Request

Client: {client_name}
Amount: ${amount:.2f}
Order ID: {order_id}

Please verify and confirm this transaction."""
    
    try:
        result = await send_telegram_message(chat_id, message)
        return {'success': result, 'message': 'Notification sent' if result else 'Failed to send'}
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        return {'success': False, 'message': str(e)}
