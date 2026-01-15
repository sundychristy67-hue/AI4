from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional
from datetime import datetime, timezone
from models import UserCreate, UserLogin, UserResponse, TokenResponse, UserRole
from auth import hash_password, verify_password, create_access_token, create_refresh_token, get_current_user
from database import fetch_one, execute, row_to_dict
from utils import generate_id, generate_referral_code, get_current_utc
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/auth', tags=['Auth'])

@router.post('/register', response_model=TokenResponse)
async def register(user_data: UserCreate):
    """Register a new user (for admin dashboard)."""
    # Check if email exists
    existing = await fetch_one(
        "SELECT id FROM users WHERE LOWER(email) = LOWER($1)", user_data.email
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Email already registered')
    
    # Generate unique referral code
    referral_code = generate_referral_code()
    while await fetch_one("SELECT id FROM users WHERE referral_code = $1", referral_code):
        referral_code = generate_referral_code()
    
    user_id = generate_id()
    
    await execute(
        """
        INSERT INTO users (id, email, username, password_hash, referral_code, referred_by, role, is_active, is_verified, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, FALSE, $8)
        """,
        user_id,
        user_data.email.lower(),
        user_data.username,
        hash_password(user_data.password),
        referral_code,
        user_data.referral_code.upper() if user_data.referral_code else None,
        UserRole.USER.value,
        get_current_utc()
    )
    
    # Create tokens
    access_token = create_access_token(data={'sub': user_id})
    refresh_token = create_refresh_token(data={'sub': user_id})
    
    user_response = UserResponse(
        id=user_id,
        email=user_data.email.lower(),
        username=user_data.username,
        referral_code=referral_code,
        referred_by=user_data.referral_code.upper() if user_data.referral_code else None,
        role=UserRole.USER,
        is_active=True,
        is_verified=False,
        created_at=datetime.now(timezone.utc)
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_response
    )


@router.post('/login', response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login a user."""
    user = await fetch_one(
        "SELECT * FROM users WHERE LOWER(email) = LOWER($1)", credentials.email
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials')
    
    user = row_to_dict(user)
    
    if not verify_password(credentials.password, user['password_hash']):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials')
    
    if not user.get('is_active', True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Account disabled')
    
    access_token = create_access_token(data={'sub': user['id']})
    refresh_token = create_refresh_token(data={'sub': user['id']})
    
    user_response = UserResponse(
        id=user['id'],
        email=user['email'],
        username=user['username'],
        referral_code=user.get('referral_code'),
        referred_by=user.get('referred_by'),
        role=UserRole(user.get('role', 'user')),
        is_active=user.get('is_active', True),
        is_verified=user.get('is_verified', False),
        created_at=user.get('created_at', datetime.now(timezone.utc))
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_response
    )


@router.get('/me', response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user."""
    return UserResponse(
        id=current_user['id'],
        email=current_user['email'],
        username=current_user['username'],
        referral_code=current_user.get('referral_code'),
        referred_by=current_user.get('referred_by'),
        role=UserRole(current_user.get('role', 'user')),
        is_active=current_user.get('is_active', True),
        is_verified=current_user.get('is_verified', False),
        created_at=current_user.get('created_at', datetime.now(timezone.utc))
    )
