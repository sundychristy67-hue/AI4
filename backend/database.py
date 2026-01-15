"""
PostgreSQL Database Connection Module
Uses asyncpg for async operations with SQLAlchemy for ORM
"""
import asyncpg
from config import settings
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Global connection pool
_pool: asyncpg.Pool = None


async def get_pool():
    """Get the database connection pool."""
    global _pool
    if _pool is None:
        raise Exception("Database pool not initialized. Call connect_to_db() first.")
    return _pool


async def get_database():
    """Get a database connection from the pool."""
    pool = await get_pool()
    return pool


async def connect_to_db():
    """Connect to PostgreSQL and initialize the database."""
    global _pool
    logger.info('Connecting to PostgreSQL...')
    
    try:
        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        
        # Create tables
        await create_tables()
        
        logger.info('Connected to PostgreSQL and created tables')
    except Exception as e:
        logger.error(f'Failed to connect to PostgreSQL: {e}')
        raise


async def close_db_connection():
    """Close the database connection pool."""
    global _pool
    if _pool:
        logger.info('Closing PostgreSQL connection...')
        await _pool.close()
        _pool = None
        logger.info('PostgreSQL connection closed')


async def create_tables():
    """Create all database tables if they don't exist."""
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        # Users table (for admin dashboard)
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(36) PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(100) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                referral_code VARCHAR(20) UNIQUE,
                referred_by VARCHAR(20),
                role VARCHAR(20) DEFAULT 'user',
                is_active BOOLEAN DEFAULT TRUE,
                is_verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Clients table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                client_id VARCHAR(36) PRIMARY KEY,
                chatwoot_contact_id VARCHAR(100) UNIQUE,
                messenger_psid VARCHAR(100),
                display_name VARCHAR(100),
                username VARCHAR(50) UNIQUE,
                password_hash VARCHAR(255),
                password_auth_enabled BOOLEAN DEFAULT FALSE,
                password_set_at TIMESTAMPTZ,
                status VARCHAR(20) DEFAULT 'active',
                withdraw_locked BOOLEAN DEFAULT FALSE,
                load_locked BOOLEAN DEFAULT FALSE,
                bonus_locked BOOLEAN DEFAULT FALSE,
                referred_by_code VARCHAR(20),
                referral_code VARCHAR(20) UNIQUE,
                referral_locked BOOLEAN DEFAULT FALSE,
                referral_count INTEGER DEFAULT 0,
                valid_referral_count INTEGER DEFAULT 0,
                referral_tier INTEGER DEFAULT 0,
                referral_percentage FLOAT DEFAULT 5.0,
                bonus_claims INTEGER DEFAULT 0,
                visibility_level VARCHAR(20) DEFAULT 'full',
                last_ip VARCHAR(45),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                last_active_at TIMESTAMPTZ
            )
        ''')
        
        # Games table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS games (
                id VARCHAR(36) PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                tagline VARCHAR(500),
                thumbnail VARCHAR(500),
                icon_url VARCHAR(500),
                category VARCHAR(100),
                download_url VARCHAR(500),
                platforms TEXT[] DEFAULT ARRAY['android'],
                availability_status VARCHAR(20) DEFAULT 'available',
                show_credentials BOOLEAN DEFAULT TRUE,
                allow_recharge BOOLEAN DEFAULT TRUE,
                is_featured BOOLEAN DEFAULT FALSE,
                display_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_by VARCHAR(36),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Portal sessions table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS portal_sessions (
                id SERIAL PRIMARY KEY,
                token VARCHAR(255) UNIQUE NOT NULL,
                client_id VARCHAR(36) REFERENCES clients(client_id) ON DELETE CASCADE,
                expires_at TIMESTAMPTZ NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Ledger transactions table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS ledger_transactions (
                id SERIAL PRIMARY KEY,
                transaction_id VARCHAR(36) UNIQUE NOT NULL,
                client_id VARCHAR(36) REFERENCES clients(client_id) ON DELETE CASCADE,
                type VARCHAR(30) NOT NULL,
                amount FLOAT NOT NULL,
                wallet_type VARCHAR(10) DEFAULT 'real',
                status VARCHAR(20) DEFAULT 'pending',
                source VARCHAR(50),
                order_id VARCHAR(36),
                reason TEXT,
                idempotency_key VARCHAR(100) UNIQUE,
                original_amount FLOAT,
                metadata JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                confirmed_at TIMESTAMPTZ,
                confirmed_by VARCHAR(36)
            )
        ''')
        
        # Orders table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                order_id VARCHAR(36) UNIQUE NOT NULL,
                client_id VARCHAR(36) REFERENCES clients(client_id) ON DELETE CASCADE,
                order_type VARCHAR(20) NOT NULL,
                game VARCHAR(200),
                game_id VARCHAR(36),
                amount FLOAT NOT NULL,
                wallet_type VARCHAR(10) DEFAULT 'real',
                original_amount FLOAT,
                username VARCHAR(100),
                password VARCHAR(100),
                payment_method VARCHAR(50),
                payout_tag VARCHAR(100),
                status VARCHAR(30) DEFAULT 'draft',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                confirmed_at TIMESTAMPTZ,
                confirmed_by VARCHAR(36),
                rejection_reason TEXT
            )
        ''')
        
        # Client credentials table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS client_credentials (
                id VARCHAR(36) PRIMARY KEY,
                client_id VARCHAR(36) REFERENCES clients(client_id) ON DELETE CASCADE,
                game_id VARCHAR(36) REFERENCES games(id) ON DELETE CASCADE,
                game_user_id VARCHAR(255),
                game_password VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                assigned_at TIMESTAMPTZ DEFAULT NOW(),
                last_accessed_at TIMESTAMPTZ,
                UNIQUE(client_id, game_id)
            )
        ''')
        
        # Client referrals table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS client_referrals (
                id VARCHAR(36) PRIMARY KEY,
                referrer_client_id VARCHAR(36) REFERENCES clients(client_id) ON DELETE CASCADE,
                referred_client_id VARCHAR(36) REFERENCES clients(client_id) ON DELETE CASCADE UNIQUE,
                status VARCHAR(20) DEFAULT 'pending',
                total_deposits FLOAT DEFAULT 0,
                fraud_flags TEXT[],
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Audit logs table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id VARCHAR(36) PRIMARY KEY,
                admin_id VARCHAR(36),
                action VARCHAR(100) NOT NULL,
                entity_type VARCHAR(50),
                entity_id VARCHAR(100),
                details JSONB,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Global settings table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS global_settings (
                id VARCHAR(20) PRIMARY KEY DEFAULT 'global',
                automation_enabled BOOLEAN DEFAULT TRUE,
                withdrawals_enabled BOOLEAN DEFAULT TRUE,
                bonus_system_enabled BOOLEAN DEFAULT TRUE,
                referral_system_enabled BOOLEAN DEFAULT TRUE,
                default_visibility VARCHAR(20) DEFAULT 'full',
                min_withdrawal_amount FLOAT DEFAULT 20.0,
                max_withdrawal_amount FLOAT DEFAULT 10000.0,
                withdrawal_fee_percentage FLOAT DEFAULT 0.0,
                referral_tier_config JSONB,
                bonus_rules JSONB,
                anti_fraud JSONB,
                active_referral_criteria JSONB,
                first_time_greeting JSONB,
                telegram_config JSONB,
                updated_at TIMESTAMPTZ,
                updated_by VARCHAR(36)
            )
        ''')
        
        # AI Test Logs table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS ai_test_logs (
                id VARCHAR(36) PRIMARY KEY,
                admin_id VARCHAR(36),
                scenario VARCHAR(100),
                messages JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Create indexes for better performance
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_clients_referral_code ON clients(referral_code)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_clients_username ON clients(username)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_ledger_client_id ON ledger_transactions(client_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_ledger_order_id ON ledger_transactions(order_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_orders_client_id ON orders(client_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_portal_sessions_token ON portal_sessions(token)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON client_referrals(referrer_client_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp)')
        
        logger.info('All database tables and indexes created')


# Helper functions for common database operations
async def fetch_one(query: str, *args):
    """Fetch a single row from the database."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def fetch_all(query: str, *args):
    """Fetch all rows from the database."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def execute(query: str, *args):
    """Execute a query (INSERT, UPDATE, DELETE)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)


async def execute_many(query: str, args_list):
    """Execute a query with multiple sets of arguments."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.executemany(query, args_list)


def row_to_dict(row):
    """Convert an asyncpg Record to a dictionary."""
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows):
    """Convert a list of asyncpg Records to a list of dictionaries."""
    return [dict(row) for row in rows] if rows else []
