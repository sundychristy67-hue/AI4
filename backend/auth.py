from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional
from config import settings
from database import fetch_one, execute, row_to_dict
from utils import generate_id, get_current_utc, get_current_utc_iso
import logging

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
security = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes))
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    to_encode.update({'exp': expire, 'type': 'refresh'})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')
    
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get('sub')
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')
    
    user = await fetch_one(
        "SELECT id, email, username, referral_code, referred_by, role, is_active, is_verified, created_at FROM users WHERE id = $1",
        user_id
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found')
    
    return row_to_dict(user)

async def get_current_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get('role') != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Admin access required')
    return current_user

async def verify_internal_api_key(x_internal_api_key: str = Header(None)):
    if not x_internal_api_key or x_internal_api_key != settings.internal_api_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid internal API key')
    return True

# ==================== PORTAL AUTH ====================

async def create_portal_session(client_id: str) -> dict:
    """Create a new portal session for a client."""
    token = generate_id()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.portal_token_expire_hours)
    
    await execute(
        """
        INSERT INTO portal_sessions (token, client_id, expires_at, is_active, created_at)
        VALUES ($1, $2, $3, TRUE, $4)
        """,
        token, client_id, expires_at, get_current_utc()
    )
    
    portal_url = f"{settings.portal_base_url}/p/{token}"
    
    return {
        'token': token,
        'portal_url': portal_url,
        'expires_at': expires_at.isoformat(),
        'client_id': client_id
    }

async def validate_portal_token(token: str) -> Optional[dict]:
    """Validate a portal token and return the client if valid."""
    session = await fetch_one(
        "SELECT * FROM portal_sessions WHERE token = $1", token
    )
    if not session:
        return None
    
    session = row_to_dict(session)
    
    # Check expiration
    expires_at = session['expires_at']
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    
    # Check if active
    if not session.get('is_active', True):
        return None
    
    # Get client
    client = await fetch_one(
        "SELECT * FROM clients WHERE client_id = $1", session['client_id']
    )
    if not client:
        return None
    
    client = row_to_dict(client)
    # Convert datetime fields to ISO strings
    if client.get('created_at'):
        client['created_at'] = client['created_at'].isoformat()
    if client.get('last_active_at'):
        client['last_active_at'] = client['last_active_at'].isoformat()
    
    return client

async def get_portal_client(x_portal_token: str = Header(None)):
    """Dependency to get current portal client from header."""
    if not x_portal_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Portal token required')
    
    client = await validate_portal_token(x_portal_token)
    if not client:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid or expired portal token')
    
    return client

async def revoke_client_sessions(client_id: str):
    """Revoke all portal sessions for a client."""
    await execute(
        "UPDATE portal_sessions SET is_active = FALSE WHERE client_id = $1",
        client_id
    )

# ==================== CLIENT PASSWORD AUTH ====================

async def create_client_access_token(client_id: str) -> str:
    """Create a JWT access token for client password auth."""
    data = {
        'sub': client_id,
        'type': 'client_auth'
    }
    return create_access_token(data, expires_delta=timedelta(days=7))

async def authenticate_client_password(username: str, password: str) -> Optional[dict]:
    """Authenticate a client using username/password."""
    # Find client by username
    client = await fetch_one(
        "SELECT * FROM clients WHERE LOWER(username) = LOWER($1)", username
    )
    if not client:
        return None
    
    client = row_to_dict(client)
    
    # Verify password
    if not client.get('password_hash'):
        return None
    
    if not verify_password(password, client['password_hash']):
        return None
    
    # Check if client is active
    if client.get('status') == 'banned':
        return None
    
    # Convert datetime fields
    if client.get('created_at'):
        client['created_at'] = client['created_at'].isoformat()
    if client.get('last_active_at'):
        client['last_active_at'] = client['last_active_at'].isoformat()
    
    return client

async def get_portal_client_from_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get portal client from JWT token (for password auth)."""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')
    
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        client_id: str = payload.get('sub')
        token_type: str = payload.get('type')
        
        if token_type != 'client_auth' or not client_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token type')
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')
    
    client = await fetch_one(
        "SELECT * FROM clients WHERE client_id = $1", client_id
    )
    if not client:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Client not found')
    
    client = row_to_dict(client)
    
    if client.get('status') == 'banned':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Account is banned')
    
    # Convert datetime fields
    if client.get('created_at'):
        client['created_at'] = client['created_at'].isoformat()
    if client.get('last_active_at'):
        client['last_active_at'] = client['last_active_at'].isoformat()
    
    return client

async def get_portal_client_flexible(
    x_portal_token: str = Header(None),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Flexible client auth - accepts either:
    1. X-Portal-Token header (magic link)
    2. Authorization Bearer token (password auth)
    """
    # Try magic link token first
    if x_portal_token:
        client = await validate_portal_token(x_portal_token)
        if client:
            return client
    
    # Try JWT auth
    if credentials:
        try:
            payload = jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            client_id: str = payload.get('sub')
            token_type: str = payload.get('type')
            
            if token_type == 'client_auth' and client_id:
                client = await fetch_one(
                    "SELECT * FROM clients WHERE client_id = $1", client_id
                )
                if client:
                    client = row_to_dict(client)
                    if client.get('status') != 'banned':
                        # Convert datetime fields
                        if client.get('created_at'):
                            client['created_at'] = client['created_at'].isoformat()
                        if client.get('last_active_at'):
                            client['last_active_at'] = client['last_active_at'].isoformat()
                        return client
        except JWTError:
            pass
    
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid or expired authentication')
