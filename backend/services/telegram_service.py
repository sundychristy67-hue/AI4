"""
Telegram Bot Service
Handles sending notifications and receiving admin commands for payment verification.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_ADMIN_CHAT_ID = os.environ.get('TELEGRAM_ADMIN_CHAT_ID')

# Initialize bot
bot = None
if TELEGRAM_BOT_TOKEN:
    bot = Bot(token=TELEGRAM_BOT_TOKEN)


async def send_message(chat_id: str, text: str, parse_mode: str = ParseMode.HTML, reply_markup=None) -> bool:
    """Send a simple text message."""
    if not bot:
        logger.error("Telegram bot not configured")
        return False
    
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )
        return True
    except TelegramError as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


async def send_admin_notification(text: str, reply_markup=None) -> bool:
    """Send notification to admin chat."""
    if not TELEGRAM_ADMIN_CHAT_ID:
        logger.warning("TELEGRAM_ADMIN_CHAT_ID not set")
        return False
    
    return await send_message(TELEGRAM_ADMIN_CHAT_ID, text, reply_markup=reply_markup)


async def notify_new_deposit(
    order_id: str,
    client_name: str,
    amount: float,
    payment_method: str,
    reference: Optional[str] = None,
    admin_chat_id: Optional[str] = None
) -> bool:
    """
    Send notification for new deposit request with inline keyboard for admin actions.
    """
    text = f"""
💰 <b>NEW DEPOSIT REQUEST</b>

👤 <b>Client:</b> {client_name}
💵 <b>Amount:</b> ${amount:.2f}
💳 <b>Method:</b> {payment_method}
🔖 <b>Reference:</b> {reference or 'N/A'}
📋 <b>Order ID:</b> <code>{order_id[:16]}...</code>

<i>Use buttons below to process this request:</i>
"""
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{order_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{order_id}")
        ],
        [
            InlineKeyboardButton("✏️ Edit Amount", callback_data=f"edit_{order_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    chat_id = admin_chat_id or TELEGRAM_ADMIN_CHAT_ID
    if chat_id:
        return await send_message(chat_id, text, reply_markup=reply_markup)
    return False


async def notify_new_withdrawal(
    order_id: str,
    client_name: str,
    amount: float,
    payout_method: str,
    payout_details: Optional[str] = None,
    admin_chat_id: Optional[str] = None
) -> bool:
    """
    Send notification for new withdrawal request with inline keyboard.
    """
    text = f"""
🏧 <b>NEW WITHDRAWAL REQUEST</b>

👤 <b>Client:</b> {client_name}
💵 <b>Amount:</b> ${amount:.2f}
💳 <b>Payout To:</b> {payout_method}
📝 <b>Details:</b> {payout_details or 'N/A'}
📋 <b>Order ID:</b> <code>{order_id[:16]}...</code>

<i>Use buttons below to process this request:</i>
"""
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm & Payout", callback_data=f"confirm_{order_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{order_id}")
        ],
        [
            InlineKeyboardButton("✏️ Edit Amount", callback_data=f"edit_{order_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    chat_id = admin_chat_id or TELEGRAM_ADMIN_CHAT_ID
    if chat_id:
        return await send_message(chat_id, text, reply_markup=reply_markup)
    return False


async def notify_order_confirmed(
    order_id: str,
    order_type: str,
    client_name: str,
    amount: float,
    new_balance: float,
    admin_name: Optional[str] = None,
    admin_chat_id: Optional[str] = None
) -> bool:
    """
    Send notification when order is confirmed.
    """
    emoji = "💰" if order_type in ["create", "cashin", "deposit"] else "🏧"
    action = "DEPOSIT" if order_type in ["create", "cashin", "deposit"] else "WITHDRAWAL"
    
    text = f"""
{emoji} <b>{action} CONFIRMED</b>

👤 <b>Client:</b> {client_name}
💵 <b>Amount:</b> ${amount:.2f}
💰 <b>New Balance:</b> ${new_balance:.2f}
✅ <b>Confirmed by:</b> {admin_name or 'Admin'}

<i>Order ID: {order_id[:16]}...</i>
"""
    
    chat_id = admin_chat_id or TELEGRAM_ADMIN_CHAT_ID
    if chat_id:
        return await send_message(chat_id, text)
    return False


async def notify_order_rejected(
    order_id: str,
    order_type: str,
    client_name: str,
    amount: float,
    reason: str,
    admin_name: Optional[str] = None,
    admin_chat_id: Optional[str] = None
) -> bool:
    """
    Send notification when order is rejected.
    """
    emoji = "💰" if order_type in ["create", "cashin", "deposit"] else "🏧"
    action = "DEPOSIT" if order_type in ["create", "cashin", "deposit"] else "WITHDRAWAL"
    
    text = f"""
❌ <b>{action} REJECTED</b>

👤 <b>Client:</b> {client_name}
💵 <b>Amount:</b> ${amount:.2f}
📝 <b>Reason:</b> {reason}
🚫 <b>Rejected by:</b> {admin_name or 'Admin'}

<i>Order ID: {order_id[:16]}...</i>
"""
    
    chat_id = admin_chat_id or TELEGRAM_ADMIN_CHAT_ID
    if chat_id:
        return await send_message(chat_id, text)
    return False


async def send_pending_orders_list(orders: List[Dict[str, Any]], admin_chat_id: Optional[str] = None) -> bool:
    """
    Send a summary of all pending orders.
    """
    if not orders:
        text = "📋 <b>No pending orders</b>\n\nAll orders have been processed!"
    else:
        text = f"📋 <b>PENDING ORDERS ({len(orders)})</b>\n\n"
        
        for i, order in enumerate(orders[:10], 1):
            order_type = "💰" if order.get('order_type') in ['create', 'cashin'] else "🏧"
            text += f"{i}. {order_type} {order.get('client_name', 'Unknown')} - ${order.get('amount', 0):.2f}\n"
            text += f"   <code>{order.get('order_id', '')[:12]}...</code>\n\n"
        
        if len(orders) > 10:
            text += f"\n<i>...and {len(orders) - 10} more orders</i>"
    
    chat_id = admin_chat_id or TELEGRAM_ADMIN_CHAT_ID
    if chat_id:
        return await send_message(chat_id, text)
    return False


async def test_bot_connection() -> Dict[str, Any]:
    """Test if bot is properly configured."""
    if not bot:
        return {"success": False, "error": "Bot not configured - missing TELEGRAM_BOT_TOKEN"}
    
    try:
        bot_info = await bot.get_me()
        return {
            "success": True,
            "bot_username": bot_info.username,
            "bot_name": bot_info.first_name,
            "bot_id": bot_info.id
        }
    except TelegramError as e:
        return {"success": False, "error": str(e)}


# Alias for send_message used by routes
async def send_telegram_message(chat_id: str, text: str, parse_mode: str = ParseMode.HTML) -> bool:
    """Send a message to a specific chat ID."""
    return await send_message(chat_id, text, parse_mode=parse_mode)
