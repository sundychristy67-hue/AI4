from motor.motor_asyncio import AsyncIOMotorClient
from config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    
database = Database()

async def get_database():
    return database.client[settings.db_name]

async def connect_to_mongo():
    logger.info('Connecting to MongoDB...')
    database.client = AsyncIOMotorClient(settings.mongo_url)
    
    # Create indexes
    db = database.client[settings.db_name]
    
    # Client indexes
    await db.clients.create_index('client_id', unique=True)
    await db.clients.create_index('chatwoot_contact_id', unique=True, sparse=True)
    await db.clients.create_index('referral_code', unique=True, sparse=True)
    
    # Portal session indexes
    await db.portal_sessions.create_index('token', unique=True)
    await db.portal_sessions.create_index('client_id')
    await db.portal_sessions.create_index('expires_at')
    
    # Ledger indexes
    await db.ledger_transactions.create_index('transaction_id', unique=True)
    await db.ledger_transactions.create_index('client_id')
    await db.ledger_transactions.create_index('idempotency_key', unique=True, sparse=True)
    await db.ledger_transactions.create_index('order_id', sparse=True)
    
    # Order indexes
    await db.orders.create_index('order_id', unique=True)
    await db.orders.create_index('client_id')
    
    # Client credentials indexes
    await db.client_credentials.create_index([('client_id', 1), ('game_id', 1)], unique=True)
    
    # User indexes (for admin/dashboard)
    await db.users.create_index('id', unique=True)
    await db.users.create_index('email', unique=True)
    await db.users.create_index('referral_code', unique=True, sparse=True)
    
    # Games
    await db.games.create_index('id', unique=True)
    
    # Client referrals
    await db.client_referrals.create_index('id', unique=True)
    await db.client_referrals.create_index('referrer_client_id')
    await db.client_referrals.create_index('referred_client_id', unique=True, sparse=True)
    
    # Audit log indexes
    await db.audit_logs.create_index('timestamp')
    await db.audit_logs.create_index('admin_id')
    
    logger.info('Connected to MongoDB and created indexes')

async def close_mongo_connection():
    logger.info('Closing MongoDB connection...')
    database.client.close()
    logger.info('MongoDB connection closed')
