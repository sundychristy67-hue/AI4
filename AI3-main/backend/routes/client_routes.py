from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from models import (
    ClientCreate, ClientUpdate, ClientResponse, ClientStatus, VisibilityLevel,
    PortalSessionCreate, PortalSessionResponse, PortalValidateResponse,
    ApplyReferralRequest, ApplyReferralResponse
)
from auth import get_current_admin, verify_internal_api_key, create_portal_session, validate_portal_token, revoke_client_sessions
from database import get_database
from utils import generate_id, generate_referral_code, get_current_utc_iso, apply_referral_code
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/clients', tags=['Clients'])

# ==================== INTERNAL API (for middleware) ====================

@router.post('/upsert', response_model=ClientResponse)
async def upsert_client(
    client_data: ClientCreate,
    _: bool = Depends(verify_internal_api_key)
):
    """Upsert a client by chatwoot_contact_id."""
    db = await get_database()
    
    # Check if client exists by chatwoot_contact_id
    existing = None
    if client_data.chatwoot_contact_id:
        existing = await db.clients.find_one(
            {'chatwoot_contact_id': client_data.chatwoot_contact_id},
            {'_id': 0}
        )
    
    if existing:
        await db.clients.update_one(
            {'chatwoot_contact_id': client_data.chatwoot_contact_id},
            {'$set': {'last_active_at': get_current_utc_iso()}}
        )
        existing['last_active_at'] = get_current_utc_iso()
        return ClientResponse(**existing)
    
    # Create new client
    client_id = generate_id()
    referral_code = generate_referral_code()
    
    while await db.clients.find_one({'referral_code': referral_code}):
        referral_code = generate_referral_code()
    
    client_doc = {
        'client_id': client_id,
        'chatwoot_contact_id': client_data.chatwoot_contact_id,
        'messenger_psid': client_data.messenger_psid,
        'display_name': client_data.display_name or f'Player_{client_id[:8]}',
        'status': ClientStatus.ACTIVE.value,
        'withdraw_locked': False,
        'load_locked': False,
        'bonus_locked': False,
        'referral_code': referral_code,
        'referred_by_code': None,
        'referral_locked': False,
        'referral_count': 0,
        'valid_referral_count': 0,
        'bonus_claims': 0,
        'created_at': get_current_utc_iso(),
        'last_active_at': get_current_utc_iso()
    }
    
    await db.clients.insert_one(client_doc)
    logger.info(f"Created new client: {client_id}")
    
    return ClientResponse(**client_doc)


@router.post('/portal-session', response_model=PortalSessionResponse)
async def create_portal_session_endpoint(
    session_data: PortalSessionCreate,
    _: bool = Depends(verify_internal_api_key)
):
    """Create a portal magic link session for a client."""
    db = await get_database()
    
    client = None
    if session_data.client_id:
        client = await db.clients.find_one({'client_id': session_data.client_id}, {'_id': 0})
    elif session_data.chatwoot_contact_id:
        client = await db.clients.find_one({'chatwoot_contact_id': session_data.chatwoot_contact_id}, {'_id': 0})
    
    if not client:
        # Create client first
        client_id = generate_id()
        referral_code = generate_referral_code()
        
        client = {
            'client_id': client_id,
            'chatwoot_contact_id': session_data.chatwoot_contact_id,
            'messenger_psid': None,
            'display_name': f'Player_{client_id[:8]}',
            'status': ClientStatus.ACTIVE.value,
            'withdraw_locked': False,
            'load_locked': False,
            'bonus_locked': False,
            'referral_code': referral_code,
            'referred_by_code': None,
            'referral_locked': False,
            'referral_count': 0,
            'valid_referral_count': 0,
            'bonus_claims': 0,
            'created_at': get_current_utc_iso(),
            'last_active_at': get_current_utc_iso()
        }
        await db.clients.insert_one(client)
    
    if client.get('status') == 'banned':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Client account is banned')
    
    session = await create_portal_session(client['client_id'])
    return PortalSessionResponse(**session)


@router.get('/all', response_model=List[ClientResponse])
async def get_all_clients(current_user: dict = Depends(get_current_admin)):
    """Get all clients (admin only)"""
    db = await get_database()
    clients = await db.clients.find({}, {'_id': 0}).sort('created_at', -1).to_list(1000)
    return [ClientResponse(**c) for c in clients]


@router.get('/{client_id}', response_model=ClientResponse)
async def get_client(client_id: str, current_user: dict = Depends(get_current_admin)):
    """Get a specific client (admin only)"""
    db = await get_database()
    client = await db.clients.find_one({'client_id': client_id}, {'_id': 0})
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Client not found')
    return ClientResponse(**client)


@router.put('/{client_id}', response_model=ClientResponse)
async def update_client(
    client_id: str,
    update_data: ClientUpdate,
    current_user: dict = Depends(get_current_admin)
):
    """Update client details (admin only)"""
    db = await get_database()
    
    client = await db.clients.find_one({'client_id': client_id}, {'_id': 0})
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Client not found')
    
    update_fields = {}
    if update_data.display_name is not None:
        update_fields['display_name'] = update_data.display_name
    if update_data.status is not None:
        update_fields['status'] = update_data.status.value
    if update_data.withdraw_locked is not None:
        update_fields['withdraw_locked'] = update_data.withdraw_locked
    if update_data.load_locked is not None:
        update_fields['load_locked'] = update_data.load_locked
    if update_data.bonus_locked is not None:
        update_fields['bonus_locked'] = update_data.bonus_locked
    if update_data.visibility_level is not None:
        update_fields['visibility_level'] = update_data.visibility_level.value
    
    if update_fields:
        await db.clients.update_one({'client_id': client_id}, {'$set': update_fields})
        
        # Log visibility change
        if update_data.visibility_level is not None:
            await db.audit_logs.insert_one({
                'admin_id': current_user['id'],
                'action': 'client_visibility_change',
                'entity_type': 'client',
                'entity_id': client_id,
                'details': {
                    'old_visibility': client.get('visibility_level', 'full'),
                    'new_visibility': update_data.visibility_level.value
                },
                'timestamp': get_current_utc_iso()
            })
    
    updated_client = await db.clients.find_one({'client_id': client_id}, {'_id': 0})
    return ClientResponse(**updated_client)


@router.post('/{client_id}/revoke-sessions')
async def revoke_all_sessions(client_id: str, current_user: dict = Depends(get_current_admin)):
    """Revoke all portal sessions for a client (admin only)"""
    db = await get_database()
    client = await db.clients.find_one({'client_id': client_id}, {'_id': 0})
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Client not found')
    
    await revoke_client_sessions(client_id)
    return {'message': 'All portal sessions revoked'}


@router.post('/{client_id}/resend-portal-link', response_model=PortalSessionResponse)
async def resend_portal_link(client_id: str, current_user: dict = Depends(get_current_admin)):
    """Generate a new portal link for a client (admin only)"""
    db = await get_database()
    client = await db.clients.find_one({'client_id': client_id}, {'_id': 0})
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Client not found')
    
    session = await create_portal_session(client_id)
    return PortalSessionResponse(**session)
