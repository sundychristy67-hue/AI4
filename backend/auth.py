from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Optional
from config import settings
from database import get_database
from utils import generate_id, get_current_utc_iso
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
    
    db = await get_database()
    user = await db.users.find_one({'id': user_id}, {'_id': 0, 'password_hash': 0})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found')
    
    return user

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
    db = await get_database()
    
    token = generate_id()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.portal_token_expire_hours)
    
    session_doc = {
        'token': token,
        'client_id': client_id,
        'created_at': get_current_utc_iso(),
        'expires_at': expires_at.isoformat(),
        'is_valid': True
    }
    
    await db.portal_sessions.insert_one(session_doc)
    
    portal_url = f"{settings.portal_base_url}/p/{token}"
    
    return {
        'token': token,
        'portal_url': portal_url,
        'expires_at': expires_at.isoformat(),
        'client_id': client_id
    }

async def validate_portal_token(token: str) -> Optional[dict]:
    """Validate a portal token and return the client if valid."""
    db = await get_database()
    
    session = await db.portal_sessions.find_one({'token': token}, {'_id': 0})
    if not session:
        return None
    
    # Check expiration
    expires_at = datetime.fromisoformat(session['expires_at'].replace('Z', '+00:00'))
    if expires_at < datetime.now(timezone.utc):
        return None
    
    # Check if valid
    if not session.get('is_valid', True):
        return None
    
    # Get client
    client = await db.clients.find_one({'client_id': session['client_id']}, {'_id': 0})
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
    db = await get_database()
    await db.portal_sessions.update_many(
        {'client_id': client_id},
        {'$set': {'is_valid': False}}
    )

# ==================== CLIENT PASSWORD AUTH ====================

async def create_client_access_token(client_id: str) -> str:
    """Create a JWT access token for client password auth."""
    data = {
        'sub': client_id,
        'type': 'client_auth',
        'iat': datetime.now(timezone.utc).isoformat()
    }
    return create_access_token(data, expires_delta=timedelta(days=7))

async def authenticate_client_password(username: str, password: str) -> Optional[dict]:
    """Authenticate a client using username/password."""
    db = await get_database()
    
    # Find client by username
    client = await db.clients.find_one({'username': username.lower()}, {'_id': 0})
    if not client:
        return None
    
    # Verify password
    if not client.get('password_hash'):
        return None
    
    if not verify_password(password, client['password_hash']):
        return None
    
    # Check if client is active
    if client.get('status') == 'banned':
        return None
    
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
    
    db = await get_database()
    client = await db.clients.find_one({'client_id': client_id}, {'_id': 0})
    if not client:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Client not found')
    
    if client.get('status') == 'banned':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Account is banned')
    
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
                db = await get_database()
                client = await db.clients.find_one({'client_id': client_id}, {'_id': 0})
                if client and client.get('status') != 'banned':
                    return client
        except JWTError:
            pass
    
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid or expired authentication')

