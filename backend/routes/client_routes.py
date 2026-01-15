from fastapi import APIRouter, HTTPException, status, Depends, Header
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from models import (
    ClientCreate, ClientResponse, ClientStatus, PortalSessionCreate, 
    PortalSessionResponse, PortalValidateResponse
)
from database import fetch_one, fetch_all, execute, row_to_dict, rows_to_list
from utils import generate_id, generate_referral_code, get_current_utc, get_current_utc_iso
from config import settings
import logging
import secrets

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/clients', tags=['Clients'])


async def verify_internal_api(x_internal_api_key: str = Header(None)):
    """Verify internal API key for system-to-system calls."""
    if x_internal_api_key != settings.internal_api_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid internal API key')
    return True


@router.post('/create', response_model=ClientResponse)
async def create_client(client_data: ClientCreate, _: bool = Depends(verify_internal_api)):
    """Create a new client (internal API - called by Chatwoot webhook)."""
    
    # Check if client already exists
    if client_data.chatwoot_contact_id:
        existing = await fetch_one(
            "SELECT client_id FROM clients WHERE chatwoot_contact_id = $1",
            client_data.chatwoot_contact_id
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Client with this Chatwoot ID already exists')
    
    # Generate unique referral code
    referral_code = generate_referral_code()
    while await fetch_one("SELECT client_id FROM clients WHERE referral_code = $1", referral_code):
        referral_code = generate_referral_code()
    
    client_id = generate_id()
    now = get_current_utc()
    
    await execute(
        """
        INSERT INTO clients (client_id, chatwoot_contact_id, messenger_psid, display_name, referral_code, created_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        client_id,
        client_data.chatwoot_contact_id,
        client_data.messenger_psid,
        client_data.display_name or 'Player',
        referral_code,
        now
    )
    
    # Fetch the created client
    client = await fetch_one("SELECT * FROM clients WHERE client_id = $1", client_id)
    client = row_to_dict(client)
    client['created_at'] = client['created_at'].isoformat() if client.get('created_at') else now.isoformat()
    if client.get('last_active_at'):
        client['last_active_at'] = client['last_active_at'].isoformat()
    
    return ClientResponse(**client)


@router.post('/portal-session', response_model=PortalSessionResponse)
async def create_portal_session(session_data: PortalSessionCreate, _: bool = Depends(verify_internal_api)):
    """Create a portal session (magic link) for a client."""
    
    # Find the client
    if session_data.client_id:
        client = await fetch_one(
            "SELECT * FROM clients WHERE client_id = $1", session_data.client_id
        )
    elif session_data.chatwoot_contact_id:
        client = await fetch_one(
            "SELECT * FROM clients WHERE chatwoot_contact_id = $1", session_data.chatwoot_contact_id
        )
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='client_id or chatwoot_contact_id required')
    
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Client not found')
    
    client = row_to_dict(client)
    
    # Check client status
    if client.get('status') == 'banned':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Client is banned')
    
    # Generate unique token
    token = secrets.token_urlsafe(32)
    
    # Calculate expiration
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.portal_token_expire_hours)
    
    # Create session
    await execute(
        """
        INSERT INTO portal_sessions (token, client_id, expires_at, is_active, created_at)
        VALUES ($1, $2, $3, TRUE, $4)
        """,
        token, client['client_id'], expires_at, get_current_utc()
    )
    
    portal_url = f"{settings.portal_base_url}/p/{token}"
    
    return PortalSessionResponse(
        token=token,
        portal_url=portal_url,
        expires_at=expires_at.isoformat(),
        client_id=client['client_id']
    )


@router.get('/{client_id}', response_model=ClientResponse)
async def get_client(client_id: str, _: bool = Depends(verify_internal_api)):
    """Get client by ID."""
    client = await fetch_one("SELECT * FROM clients WHERE client_id = $1", client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Client not found')
    
    client = row_to_dict(client)
    client['created_at'] = client['created_at'].isoformat() if client.get('created_at') else get_current_utc_iso()
    if client.get('last_active_at'):
        client['last_active_at'] = client['last_active_at'].isoformat()
    
    return ClientResponse(**client)


@router.get('/by-chatwoot/{chatwoot_contact_id}', response_model=ClientResponse)
async def get_client_by_chatwoot(chatwoot_contact_id: str, _: bool = Depends(verify_internal_api)):
    """Get client by Chatwoot contact ID."""
    client = await fetch_one(
        "SELECT * FROM clients WHERE chatwoot_contact_id = $1", chatwoot_contact_id
    )
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Client not found')
    
    client = row_to_dict(client)
    client['created_at'] = client['created_at'].isoformat() if client.get('created_at') else get_current_utc_iso()
    if client.get('last_active_at'):
        client['last_active_at'] = client['last_active_at'].isoformat()
    
    return ClientResponse(**client)


@router.get('/', response_model=List[ClientResponse])
async def list_clients(
    status: Optional[str] = None,
    limit: int = 100,
    _: bool = Depends(verify_internal_api)
):
    """List all clients."""
    if status:
        clients = await fetch_all(
            "SELECT * FROM clients WHERE status = $1 ORDER BY created_at DESC LIMIT $2",
            status, limit
        )
    else:
        clients = await fetch_all(
            "SELECT * FROM clients ORDER BY created_at DESC LIMIT $1",
            limit
        )
    
    result = []
    for c in rows_to_list(clients):
        c['created_at'] = c['created_at'].isoformat() if c.get('created_at') else get_current_utc_iso()
        if c.get('last_active_at'):
            c['last_active_at'] = c['last_active_at'].isoformat()
        result.append(ClientResponse(**c))
    
    return result
