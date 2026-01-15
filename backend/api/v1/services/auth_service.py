"""
API v1 Authentication Service
Handles user authentication, magic links, and session management
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple

from ..core.database import fetch_one, fetch_all, execute, execute_returning
from ..core.security import (
    hash_password, verify_password, generate_referral_code,
    generate_magic_link_token, generate_session_token, create_jwt_token,
    decode_jwt_token, check_brute_force, record_failed_attempt, clear_failed_attempts
)
from ..core.config import get_api_settings, ErrorCodes
from ..models import SignupResponse

settings = get_api_settings()


async def create_user(
    username: str,
    password: str,
    display_name: str,
    referred_by_code: Optional[str] = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Create a new user account.
    Returns (success, data/error)
    """
    username = username.lower().strip()
    
    # Check if username exists
    existing = await fetch_one(
        "SELECT user_id FROM api_users WHERE username = $1",
        username
    )
    if existing:
        return False, {
            "message": "Username already exists",
            "error_code": ErrorCodes.USER_ALREADY_EXISTS
        }
    
    # Validate referral code if provided
    referrer_user_id = None
    if referred_by_code:
        referrer = await fetch_one(
            "SELECT user_id, username FROM api_users WHERE referral_code = $1 AND is_active = TRUE",
            referred_by_code.upper()
        )
        if not referrer:
            return False, {
                "message": "Invalid referral code",
                "error_code": ErrorCodes.INVALID_REFERRAL_CODE
            }
        referrer_user_id = referrer['user_id']
    
    # Generate unique referral code
    referral_code = generate_referral_code()
    while await fetch_one("SELECT user_id FROM api_users WHERE referral_code = $1", referral_code):
        referral_code = generate_referral_code()
    
    # Create user
    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)
    
    await execute('''
        INSERT INTO api_users (user_id, username, password_hash, display_name, referral_code, referred_by_code, referred_by_user_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
    ''', user_id, username, password_hash, display_name, referral_code,
       referred_by_code.upper() if referred_by_code else None, referrer_user_id)
    
    # Log audit
    await log_audit(user_id, username, "user.signup", "user", user_id, {
        "referred_by": referred_by_code
    })
    
    return True, {
        "user_id": user_id,
        "username": username,
        "display_name": display_name,
        "referral_code": referral_code,
        "referred_by_code": referred_by_code.upper() if referred_by_code else None
    }


async def authenticate_user(username: str, password: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Authenticate user with username and password.
    Returns (success, user_data/error)
    """
    username = username.lower().strip()
    
    # Check brute force lockout
    is_allowed, lockout_remaining = check_brute_force(username)
    if not is_allowed:
        return False, {
            "message": f"Account temporarily locked. Try again in {lockout_remaining} seconds",
            "error_code": ErrorCodes.ACCOUNT_LOCKED,
            "lockout_remaining": lockout_remaining
        }
    
    # Get user
    user = await fetch_one(
        "SELECT * FROM api_users WHERE username = $1",
        username
    )
    
    if not user:
        record_failed_attempt(username)
        return False, {
            "message": "Invalid credentials",
            "error_code": ErrorCodes.INVALID_CREDENTIALS
        }
    
    # Verify password
    if not verify_password(password, user['password_hash']):
        record_failed_attempt(username)
        return False, {
            "message": "Invalid credentials",
            "error_code": ErrorCodes.INVALID_CREDENTIALS
        }
    
    # Check if active
    if not user.get('is_active', True):
        return False, {
            "message": "Account is disabled",
            "error_code": ErrorCodes.ACCOUNT_LOCKED
        }
    
    # Clear failed attempts
    clear_failed_attempts(username)
    
    return True, {
        "user_id": user['user_id'],
        "username": user['username'],
        "display_name": user['display_name'],
        "referral_code": user['referral_code']
    }


async def create_magic_link(user_id: str, username: str) -> Dict[str, Any]:
    """
    Create a magic link for user authentication.
    Returns magic link data.
    """
    token = generate_magic_link_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.magic_link_expire_minutes)
    
    await execute('''
        INSERT INTO api_magic_links (user_id, token, expires_at)
        VALUES ($1, $2, $3)
    ''', user_id, token, expires_at)
    
    magic_link = f"{settings.magic_link_base_url}?token={token}"
    
    # Log audit
    await log_audit(user_id, username, "auth.magic_link_created", "magic_link", token[:16])
    
    return {
        "magic_link": magic_link,
        "token": token,
        "expires_in_seconds": settings.magic_link_expire_minutes * 60
    }


async def consume_magic_link(token: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Consume a magic link and return session token.
    Returns (success, session_data/error)
    """
    # Find magic link
    magic_link = await fetch_one('''
        SELECT ml.*, u.username, u.display_name, u.referral_code
        FROM api_magic_links ml
        JOIN api_users u ON ml.user_id = u.user_id
        WHERE ml.token = $1 AND ml.consumed = FALSE
    ''', token)
    
    if not magic_link:
        return False, {
            "message": "Invalid or already used magic link",
            "error_code": ErrorCodes.INVALID_TOKEN
        }
    
    # Check expiration
    expires_at = magic_link['expires_at']
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        return False, {
            "message": "Magic link has expired",
            "error_code": ErrorCodes.TOKEN_EXPIRED
        }
    
    # Mark as consumed
    await execute('''
        UPDATE api_magic_links SET consumed = TRUE, consumed_at = $1 WHERE token = $2
    ''', datetime.now(timezone.utc), token)
    
    # Create session
    access_token = create_jwt_token({
        "sub": magic_link['user_id'],
        "username": magic_link['username'],
        "type": "access"
    })
    
    session_expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    
    await execute('''
        INSERT INTO api_sessions (user_id, access_token, expires_at)
        VALUES ($1, $2, $3)
    ''', magic_link['user_id'], access_token, session_expires)
    
    # Log audit
    await log_audit(magic_link['user_id'], magic_link['username'], "auth.magic_link_consumed", "session", access_token[:16])
    
    return True, {
        "access_token": access_token,
        "expires_in_seconds": settings.access_token_expire_minutes * 60,
        "user": {
            "user_id": magic_link['user_id'],
            "username": magic_link['username'],
            "display_name": magic_link['display_name'],
            "referral_code": magic_link['referral_code']
        }
    }


async def validate_token(token: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate an access token.
    Returns (valid, user_data/error)
    """
    # Decode JWT
    payload = decode_jwt_token(token)
    if not payload:
        return False, {"message": "Invalid token", "error_code": ErrorCodes.INVALID_TOKEN}
    
    user_id = payload.get('sub')
    if not user_id:
        return False, {"message": "Invalid token", "error_code": ErrorCodes.INVALID_TOKEN}
    
    # Verify user exists and is active
    user = await fetch_one(
        "SELECT user_id, username, display_name, referral_code, is_active FROM api_users WHERE user_id = $1",
        user_id
    )
    
    if not user or not user.get('is_active', True):
        return False, {"message": "User not found or disabled", "error_code": ErrorCodes.USER_NOT_FOUND}
    
    # Update session last used
    await execute('''
        UPDATE api_sessions SET last_used_at = $1 WHERE access_token = $2 AND is_active = TRUE
    ''', datetime.now(timezone.utc), token)
    
    return True, {
        "user_id": user['user_id'],
        "username": user['username'],
        "display_name": user['display_name'],
        "referral_code": user['referral_code'],
        "expires_at": datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
    }


async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get user by username"""
    return await fetch_one(
        "SELECT user_id, username, display_name, referral_code, is_active FROM api_users WHERE username = $1",
        username.lower()
    )


async def log_audit(
    user_id: Optional[str],
    username: Optional[str],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """Log an audit event"""
    import json
    log_id = str(uuid.uuid4())
    await execute('''
        INSERT INTO api_audit_logs (log_id, user_id, username, action, resource_type, resource_id, details, ip_address, user_agent)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    ''', log_id, user_id, username, action, resource_type, resource_id,
       json.dumps(details) if details else None, ip_address, user_agent)
