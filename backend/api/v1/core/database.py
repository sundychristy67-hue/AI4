"""
API v1 Database Module
PostgreSQL connection and table management for the v1 API
"""
import asyncpg
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import logging
import json

from .config import get_api_settings

logger = logging.getLogger(__name__)
settings = get_api_settings()

# Connection pool
_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Get the database connection pool"""
    global _pool
    if _pool is None:
        raise Exception("Database not connected. Call init_api_v1_db() first.")
    return _pool


async def init_api_v1_db():
    """Initialize API v1 database tables"""
    global _pool
    
    logger.info("Initializing API v1 database...")
    
    _pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=2,
        max_size=10
    )
    
    async with _pool.acquire() as conn:
        # API Users table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS api_users (
                user_id VARCHAR(36) PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                display_name VARCHAR(100) NOT NULL,
                referral_code VARCHAR(20) UNIQUE NOT NULL,
                referred_by_code VARCHAR(20),
                referred_by_user_id VARCHAR(36),
                referral_bonus_claimed BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Magic Links table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS api_magic_links (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(36) REFERENCES api_users(user_id) ON DELETE CASCADE,
                token VARCHAR(255) UNIQUE NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                consumed BOOLEAN DEFAULT FALSE,
                consumed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Sessions table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS api_sessions (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(36) REFERENCES api_users(user_id) ON DELETE CASCADE,
                access_token VARCHAR(255) UNIQUE NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                last_used_at TIMESTAMPTZ
            )
        ''')
        
        # Games table with bonus rules
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS api_games (
                game_id VARCHAR(36) PRIMARY KEY,
                game_name VARCHAR(100) UNIQUE NOT NULL,
                display_name VARCHAR(200) NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                min_recharge_amount FLOAT DEFAULT 10.0,
                max_recharge_amount FLOAT DEFAULT 10000.0,
                bonus_rules JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Referral Perks table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS api_referral_perks (
                perk_id VARCHAR(36) PRIMARY KEY,
                referral_code VARCHAR(20) NOT NULL,
                game_name VARCHAR(100),
                percent_bonus FLOAT DEFAULT 0.0,
                flat_bonus FLOAT DEFAULT 0.0,
                max_bonus FLOAT,
                min_amount FLOAT,
                valid_from TIMESTAMPTZ DEFAULT NOW(),
                valid_until TIMESTAMPTZ,
                max_uses INTEGER,
                current_uses INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Orders table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS api_orders (
                order_id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) REFERENCES api_users(user_id),
                username VARCHAR(50) NOT NULL,
                game_name VARCHAR(100) NOT NULL,
                game_display_name VARCHAR(200),
                recharge_amount FLOAT NOT NULL,
                bonus_amount FLOAT DEFAULT 0.0,
                total_amount FLOAT NOT NULL,
                referral_code VARCHAR(20),
                referral_bonus_applied BOOLEAN DEFAULT FALSE,
                rule_applied TEXT,
                status VARCHAR(20) DEFAULT 'pending',
                idempotency_key VARCHAR(100) UNIQUE,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Webhooks table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS api_webhooks (
                webhook_id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) REFERENCES api_users(user_id) ON DELETE CASCADE,
                webhook_url VARCHAR(500) NOT NULL,
                signing_secret VARCHAR(255) NOT NULL,
                subscribed_events TEXT[] DEFAULT ARRAY['order.created'],
                is_active BOOLEAN DEFAULT TRUE,
                failure_count INTEGER DEFAULT 0,
                last_triggered_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Webhook Deliveries table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS api_webhook_deliveries (
                delivery_id VARCHAR(36) PRIMARY KEY,
                webhook_id VARCHAR(36) REFERENCES api_webhooks(webhook_id) ON DELETE CASCADE,
                event_type VARCHAR(50) NOT NULL,
                payload JSONB NOT NULL,
                response_status INTEGER,
                response_body TEXT,
                attempt_count INTEGER DEFAULT 1,
                delivered_at TIMESTAMPTZ,
                next_retry_at TIMESTAMPTZ,
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Audit Logs table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS api_audit_logs (
                log_id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36),
                username VARCHAR(50),
                action VARCHAR(100) NOT NULL,
                resource_type VARCHAR(50),
                resource_id VARCHAR(100),
                details JSONB,
                ip_address VARCHAR(45),
                user_agent TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        ''')
        
        # Create indexes
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_api_users_username ON api_users(username)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_api_users_referral_code ON api_users(referral_code)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_api_magic_links_token ON api_magic_links(token)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_api_sessions_token ON api_sessions(access_token)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_api_orders_user ON api_orders(user_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_api_orders_idempotency ON api_orders(idempotency_key)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_api_orders_status ON api_orders(status)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_api_audit_created ON api_audit_logs(created_at)')
        
        # Seed default games if empty
        game_count = await conn.fetchval("SELECT COUNT(*) FROM api_games")
        if game_count == 0:
            import uuid
            default_games = [
                ("dragon_quest", "Dragon Quest Online", "Epic fantasy MMORPG", 10.0, 5000.0),
                ("speed_racer", "Speed Racer Pro", "High-octane racing game", 5.0, 1000.0),
                ("battle_arena", "Battle Arena", "Competitive PvP battle game", 20.0, 10000.0),
                ("puzzle_master", "Puzzle Master", "Brain-teasing puzzle game", 1.0, 500.0),
            ]
            for game_name, display_name, desc, min_amt, max_amt in default_games:
                bonus_rules = {
                    "default": {"percent_bonus": 5.0, "flat_bonus": 0, "max_bonus": max_amt * 0.1},
                    "first_recharge": {"percent_bonus": 10.0, "flat_bonus": 5.0, "max_bonus": max_amt * 0.2}
                }
                await conn.execute('''
                    INSERT INTO api_games (game_id, game_name, display_name, description, min_recharge_amount, max_recharge_amount, bonus_rules)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                ''', str(uuid.uuid4()), game_name, display_name, desc, min_amt, max_amt, json.dumps(bonus_rules))
        
        logger.info("API v1 database initialized successfully")


async def close_api_v1_db():
    """Close the database connection pool"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("API v1 database connection closed")


# Helper functions
async def fetch_one(query: str, *args) -> Optional[Dict]:
    """Fetch a single row"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def fetch_all(query: str, *args) -> List[Dict]:
    """Fetch all rows"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]


async def execute(query: str, *args) -> str:
    """Execute a query"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)


async def execute_returning(query: str, *args) -> Optional[Dict]:
    """Execute a query and return the result"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None
