"""
Admin Settings Routes
Manage global platform settings including:
- Referral tiers and commission percentages
- Bonus milestones and rewards
- Anti-fraud detection settings
- Feature toggles
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, List
from auth import get_current_admin
from database import get_database
from utils import (
    get_current_utc_iso, get_default_settings, get_global_settings,
    invalidate_settings_cache
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/admin/settings', tags=['Admin Settings'])


async def log_settings_change(db, admin_id: str, change_type: str, details: dict):
    """Log settings changes for audit."""
    log_doc = {
        'admin_id': admin_id,
        'action': f'settings_{change_type}',
        'entity_type': 'settings',
        'entity_id': 'global',
        'details': details,
        'timestamp': get_current_utc_iso()
    }
    await db.audit_logs.insert_one(log_doc)


# ==================== GET SETTINGS ====================

@router.get('')
async def get_all_settings(current_user: dict = Depends(get_current_admin)):
    """Get all global settings."""
    db = await get_database()
    settings = await get_global_settings(db)
    return settings


@router.get('/referral-tiers')
async def get_referral_tiers(current_user: dict = Depends(get_current_admin)):
    """Get referral tier configuration."""
    db = await get_database()
    settings = await get_global_settings(db)
    return settings.get('referral_tier_config', {})


@router.get('/bonus-milestones')
async def get_bonus_milestones(current_user: dict = Depends(get_current_admin)):
    """Get bonus milestones configuration."""
    db = await get_database()
    settings = await get_global_settings(db)
    return settings.get('bonus_rules', {})


@router.get('/anti-fraud')
async def get_anti_fraud_settings(current_user: dict = Depends(get_current_admin)):
    """Get anti-fraud configuration."""
    db = await get_database()
    settings = await get_global_settings(db)
    return settings.get('anti_fraud', {})


# ==================== UPDATE GLOBAL SETTINGS ====================

@router.put('')
async def update_global_settings(
    updates: dict,
    current_user: dict = Depends(get_current_admin)
):
    """Update global feature toggles and basic settings."""
    db = await get_database()
    
    allowed_fields = [
        'automation_enabled', 'withdrawals_enabled', 'bonus_system_enabled',
        'referral_system_enabled', 'min_withdrawal_amount', 'max_withdrawal_amount',
        'withdrawal_fee_percentage'
    ]
    
    update_doc = {}
    for field in allowed_fields:
        if field in updates:
            update_doc[field] = updates[field]
    
    if not update_doc:
        raise HTTPException(status_code=400, detail='No valid fields to update')
    
    update_doc['updated_at'] = get_current_utc_iso()
    update_doc['updated_by'] = current_user['id']
    
    await db.global_settings.update_one(
        {'_id': 'global'},
        {'$set': update_doc},
        upsert=True
    )
    
    invalidate_settings_cache()
    await log_settings_change(db, current_user['id'], 'global_update', update_doc)
    
    return {'message': 'Settings updated successfully', 'updated_fields': list(update_doc.keys())}


# ==================== REFERRAL TIERS ====================

@router.put('/referral-tiers')
async def update_referral_tiers(
    tiers: List[dict],
    current_user: dict = Depends(get_current_admin)
):
    """
    Replace all referral tiers with new configuration.
    
    Expected format:
    [
        {"tier_number": 0, "name": "Starter", "min_referrals": 0, "commission_percentage": 5.0},
        {"tier_number": 1, "name": "Bronze", "min_referrals": 5, "commission_percentage": 6.0},
        ...
    ]
    """
    db = await get_database()
    
    # Validate tiers
    if not tiers:
        raise HTTPException(status_code=400, detail='At least one tier is required')
    
    # Ensure tier 0 exists with min_referrals=0
    has_base_tier = any(t.get('min_referrals', -1) == 0 for t in tiers)
    if not has_base_tier:
        raise HTTPException(status_code=400, detail='Must have a base tier with min_referrals=0')
    
    # Validate each tier
    for tier in tiers:
        if 'commission_percentage' not in tier or tier['commission_percentage'] < 0:
            raise HTTPException(status_code=400, detail='Each tier must have a valid commission_percentage >= 0')
        if 'min_referrals' not in tier or tier['min_referrals'] < 0:
            raise HTTPException(status_code=400, detail='Each tier must have a valid min_referrals >= 0')
    
    # Sort by min_referrals and assign tier numbers
    tiers = sorted(tiers, key=lambda x: x.get('min_referrals', 0))
    for i, tier in enumerate(tiers):
        tier['tier_number'] = i
    
    tier_config = {
        'base_percentage': tiers[0].get('commission_percentage', 5.0),
        'tiers': tiers
    }
    
    await db.global_settings.update_one(
        {'_id': 'global'},
        {
            '$set': {
                'referral_tier_config': tier_config,
                'updated_at': get_current_utc_iso(),
                'updated_by': current_user['id']
            }
        },
        upsert=True
    )
    
    invalidate_settings_cache()
    await log_settings_change(db, current_user['id'], 'referral_tiers_update', {'tiers_count': len(tiers)})
    
    return {'message': 'Referral tiers updated successfully', 'tiers': tiers}


@router.post('/referral-tiers/add')
async def add_referral_tier(
    tier: dict,
    current_user: dict = Depends(get_current_admin)
):
    """Add a new referral tier."""
    db = await get_database()
    settings = await get_global_settings(db)
    
    tier_config = settings.get('referral_tier_config', {'tiers': []})
    tiers = tier_config.get('tiers', [])
    
    # Validate
    if 'min_referrals' not in tier or 'commission_percentage' not in tier:
        raise HTTPException(status_code=400, detail='min_referrals and commission_percentage are required')
    
    # Check for duplicate min_referrals
    if any(t.get('min_referrals') == tier['min_referrals'] for t in tiers):
        raise HTTPException(status_code=400, detail='A tier with this min_referrals already exists')
    
    # Add and re-sort
    tiers.append(tier)
    tiers = sorted(tiers, key=lambda x: x.get('min_referrals', 0))
    for i, t in enumerate(tiers):
        t['tier_number'] = i
    
    tier_config['tiers'] = tiers
    tier_config['base_percentage'] = tiers[0].get('commission_percentage', 5.0)
    
    await db.global_settings.update_one(
        {'_id': 'global'},
        {
            '$set': {
                'referral_tier_config': tier_config,
                'updated_at': get_current_utc_iso(),
                'updated_by': current_user['id']
            }
        },
        upsert=True
    )
    
    invalidate_settings_cache()
    await log_settings_change(db, current_user['id'], 'referral_tier_add', tier)
    
    return {'message': 'Tier added successfully', 'tiers': tiers}


@router.delete('/referral-tiers/{tier_number}')
async def delete_referral_tier(
    tier_number: int,
    current_user: dict = Depends(get_current_admin)
):
    """Delete a referral tier (cannot delete base tier 0)."""
    db = await get_database()
    
    if tier_number == 0:
        raise HTTPException(status_code=400, detail='Cannot delete base tier')
    
    settings = await get_global_settings(db)
    tier_config = settings.get('referral_tier_config', {'tiers': []})
    tiers = tier_config.get('tiers', [])
    
    # Find and remove tier
    new_tiers = [t for t in tiers if t.get('tier_number') != tier_number]
    
    if len(new_tiers) == len(tiers):
        raise HTTPException(status_code=404, detail='Tier not found')
    
    # Re-number tiers
    new_tiers = sorted(new_tiers, key=lambda x: x.get('min_referrals', 0))
    for i, t in enumerate(new_tiers):
        t['tier_number'] = i
    
    tier_config['tiers'] = new_tiers
    
    await db.global_settings.update_one(
        {'_id': 'global'},
        {
            '$set': {
                'referral_tier_config': tier_config,
                'updated_at': get_current_utc_iso(),
                'updated_by': current_user['id']
            }
        },
        upsert=True
    )
    
    invalidate_settings_cache()
    await log_settings_change(db, current_user['id'], 'referral_tier_delete', {'tier_number': tier_number})
    
    return {'message': 'Tier deleted successfully', 'tiers': new_tiers}


# ==================== BONUS MILESTONES ====================

@router.put('/bonus-milestones')
async def update_bonus_milestones(
    milestones: List[dict],
    current_user: dict = Depends(get_current_admin)
):
    """
    Replace all bonus milestones with new configuration.
    
    Expected format:
    [
        {"milestone_number": 1, "referrals_required": 5, "bonus_amount": 5.0, "bonus_type": "bonus", "description": "First bonus"},
        ...
    ]
    """
    db = await get_database()
    
    # Validate milestones
    for milestone in milestones:
        if 'referrals_required' not in milestone or milestone['referrals_required'] < 1:
            raise HTTPException(status_code=400, detail='Each milestone must have referrals_required >= 1')
        if 'bonus_amount' not in milestone or milestone['bonus_amount'] <= 0:
            raise HTTPException(status_code=400, detail='Each milestone must have bonus_amount > 0')
    
    # Sort by referrals_required and assign milestone numbers
    milestones = sorted(milestones, key=lambda x: x.get('referrals_required', 0))
    for i, milestone in enumerate(milestones):
        milestone['milestone_number'] = i + 1
        if 'bonus_type' not in milestone:
            milestone['bonus_type'] = 'bonus'
        if 'description' not in milestone:
            milestone['description'] = f"{milestone['referrals_required']} referrals bonus"
    
    settings = await get_global_settings(db)
    bonus_rules = settings.get('bonus_rules', {'enabled': True})
    bonus_rules['milestones'] = milestones
    
    await db.global_settings.update_one(
        {'_id': 'global'},
        {
            '$set': {
                'bonus_rules': bonus_rules,
                'updated_at': get_current_utc_iso(),
                'updated_by': current_user['id']
            }
        },
        upsert=True
    )
    
    invalidate_settings_cache()
    await log_settings_change(db, current_user['id'], 'bonus_milestones_update', {'count': len(milestones)})
    
    return {'message': 'Bonus milestones updated successfully', 'milestones': milestones}


@router.post('/bonus-milestones/add')
async def add_bonus_milestone(
    milestone: dict,
    current_user: dict = Depends(get_current_admin)
):
    """Add a new bonus milestone."""
    db = await get_database()
    settings = await get_global_settings(db)
    
    bonus_rules = settings.get('bonus_rules', {'enabled': True, 'milestones': []})
    milestones = bonus_rules.get('milestones', [])
    
    # Validate
    if 'referrals_required' not in milestone or 'bonus_amount' not in milestone:
        raise HTTPException(status_code=400, detail='referrals_required and bonus_amount are required')
    
    # Check for duplicate referrals_required
    if any(m.get('referrals_required') == milestone['referrals_required'] for m in milestones):
        raise HTTPException(status_code=400, detail='A milestone with this referrals_required already exists')
    
    # Set defaults
    if 'bonus_type' not in milestone:
        milestone['bonus_type'] = 'bonus'
    if 'description' not in milestone:
        milestone['description'] = f"{milestone['referrals_required']} referrals bonus"
    
    # Add and re-sort
    milestones.append(milestone)
    milestones = sorted(milestones, key=lambda x: x.get('referrals_required', 0))
    for i, m in enumerate(milestones):
        m['milestone_number'] = i + 1
    
    bonus_rules['milestones'] = milestones
    
    await db.global_settings.update_one(
        {'_id': 'global'},
        {
            '$set': {
                'bonus_rules': bonus_rules,
                'updated_at': get_current_utc_iso(),
                'updated_by': current_user['id']
            }
        },
        upsert=True
    )
    
    invalidate_settings_cache()
    await log_settings_change(db, current_user['id'], 'bonus_milestone_add', milestone)
    
    return {'message': 'Milestone added successfully', 'milestones': milestones}


@router.delete('/bonus-milestones/{milestone_number}')
async def delete_bonus_milestone(
    milestone_number: int,
    current_user: dict = Depends(get_current_admin)
):
    """Delete a bonus milestone."""
    db = await get_database()
    settings = await get_global_settings(db)
    
    bonus_rules = settings.get('bonus_rules', {'enabled': True, 'milestones': []})
    milestones = bonus_rules.get('milestones', [])
    
    # Find and remove milestone
    new_milestones = [m for m in milestones if m.get('milestone_number') != milestone_number]
    
    if len(new_milestones) == len(milestones):
        raise HTTPException(status_code=404, detail='Milestone not found')
    
    # Re-number milestones
    new_milestones = sorted(new_milestones, key=lambda x: x.get('referrals_required', 0))
    for i, m in enumerate(new_milestones):
        m['milestone_number'] = i + 1
    
    bonus_rules['milestones'] = new_milestones
    
    await db.global_settings.update_one(
        {'_id': 'global'},
        {
            '$set': {
                'bonus_rules': bonus_rules,
                'updated_at': get_current_utc_iso(),
                'updated_by': current_user['id']
            }
        },
        upsert=True
    )
    
    invalidate_settings_cache()
    await log_settings_change(db, current_user['id'], 'bonus_milestone_delete', {'milestone_number': milestone_number})
    
    return {'message': 'Milestone deleted successfully', 'milestones': new_milestones}


@router.put('/bonus-milestones/toggle')
async def toggle_bonus_system(
    enabled: bool,
    current_user: dict = Depends(get_current_admin)
):
    """Enable or disable the bonus system."""
    db = await get_database()
    settings = await get_global_settings(db)
    
    bonus_rules = settings.get('bonus_rules', {'milestones': []})
    bonus_rules['enabled'] = enabled
    
    await db.global_settings.update_one(
        {'_id': 'global'},
        {
            '$set': {
                'bonus_rules': bonus_rules,
                'bonus_system_enabled': enabled,
                'updated_at': get_current_utc_iso(),
                'updated_by': current_user['id']
            }
        },
        upsert=True
    )
    
    invalidate_settings_cache()
    await log_settings_change(db, current_user['id'], 'bonus_system_toggle', {'enabled': enabled})
    
    return {'message': f'Bonus system {"enabled" if enabled else "disabled"}', 'enabled': enabled}


# ==================== ANTI-FRAUD SETTINGS ====================

@router.put('/anti-fraud')
async def update_anti_fraud_settings(
    updates: dict,
    current_user: dict = Depends(get_current_admin)
):
    """Update anti-fraud detection settings."""
    db = await get_database()
    settings = await get_global_settings(db)
    
    anti_fraud = settings.get('anti_fraud', {})
    
    allowed_fields = [
        'enabled', 'max_referrals_per_ip', 'ip_cooldown_hours',
        'min_account_age_hours', 'min_deposit_for_valid_referral',
        'device_fingerprint_enabled', 'max_referrals_per_device',
        'flag_same_ip_referrals', 'flag_rapid_signups',
        'rapid_signup_threshold_minutes', 'auto_flag_suspicious',
        'auto_reject_fraud'
    ]
    
    for field in allowed_fields:
        if field in updates:
            anti_fraud[field] = updates[field]
    
    await db.global_settings.update_one(
        {'_id': 'global'},
        {
            '$set': {
                'anti_fraud': anti_fraud,
                'updated_at': get_current_utc_iso(),
                'updated_by': current_user['id']
            }
        },
        upsert=True
    )
    
    invalidate_settings_cache()
    await log_settings_change(db, current_user['id'], 'anti_fraud_update', updates)
    
    return {'message': 'Anti-fraud settings updated successfully', 'anti_fraud': anti_fraud}


# ==================== RESET TO DEFAULTS ====================

@router.post('/reset-defaults')
async def reset_to_defaults(
    section: Optional[str] = None,
    current_user: dict = Depends(get_current_admin)
):
    """
    Reset settings to defaults.
    
    section options:
    - 'all' or None: Reset everything
    - 'tiers': Reset referral tiers only
    - 'milestones': Reset bonus milestones only
    - 'antifraud': Reset anti-fraud settings only
    """
    db = await get_database()
    defaults = get_default_settings()
    
    update_doc = {
        'updated_at': get_current_utc_iso(),
        'updated_by': current_user['id']
    }
    
    if section is None or section == 'all':
        update_doc.update(defaults)
    elif section == 'tiers':
        update_doc['referral_tier_config'] = defaults['referral_tier_config']
    elif section == 'milestones':
        update_doc['bonus_rules'] = defaults['bonus_rules']
    elif section == 'antifraud':
        update_doc['anti_fraud'] = defaults['anti_fraud']
    else:
        raise HTTPException(status_code=400, detail='Invalid section. Use: all, tiers, milestones, antifraud')
    
    await db.global_settings.update_one(
        {'_id': 'global'},
        {'$set': update_doc},
        upsert=True
    )
    
    invalidate_settings_cache()
    await log_settings_change(db, current_user['id'], 'reset_defaults', {'section': section or 'all'})
    
    return {'message': f'Settings reset to defaults ({section or "all"})', 'settings': update_doc}



# ==================== ACTIVE REFERRAL CRITERIA ====================

@router.get('/active-referral-criteria')
async def get_active_referral_criteria(current_user: dict = Depends(get_current_admin)):
    """Get active referral criteria configuration."""
    db = await get_database()
    settings = await get_global_settings(db)
    return settings.get('active_referral_criteria', {
        "min_deposits_required": 1,
        "min_total_deposit_amount": 10.0,
        "activity_window_days": 30,
        "require_recent_activity": True
    })


@router.put('/active-referral-criteria')
async def update_active_referral_criteria(
    criteria: dict,
    current_user: dict = Depends(get_current_admin)
):
    """
    Update active referral criteria.
    
    Criteria defines when a referral is considered "active":
    - min_deposits_required: Minimum number of deposits
    - min_total_deposit_amount: Minimum total deposited amount
    - activity_window_days: Within how many days the activity must occur
    - require_recent_activity: Whether recent activity is required
    """
    db = await get_database()
    
    allowed_fields = [
        'min_deposits_required', 'min_total_deposit_amount', 
        'activity_window_days', 'require_recent_activity'
    ]
    
    # Validate and filter
    valid_criteria = {}
    for field in allowed_fields:
        if field in criteria:
            valid_criteria[field] = criteria[field]
    
    if not valid_criteria:
        raise HTTPException(status_code=400, detail='No valid criteria fields provided')
    
    # Get current settings and merge
    settings = await get_global_settings(db)
    current_criteria = settings.get('active_referral_criteria', {})
    current_criteria.update(valid_criteria)
    
    await db.global_settings.update_one(
        {'_id': 'global'},
        {
            '$set': {
                'active_referral_criteria': current_criteria,
                'updated_at': get_current_utc_iso(),
                'updated_by': current_user['id']
            }
        },
        upsert=True
    )
    
    invalidate_settings_cache()
    await log_settings_change(db, current_user['id'], 'active_referral_criteria_update', valid_criteria)
    
    return {'message': 'Active referral criteria updated', 'criteria': current_criteria}


# ==================== FIRST-TIME GREETING MESSAGES ====================

@router.get('/first-time-greeting')
async def get_first_time_greeting(current_user: dict = Depends(get_current_admin)):
    """Get first-time client greeting messages configuration."""
    db = await get_database()
    settings = await get_global_settings(db)
    return settings.get('first_time_greeting', {
        "enabled": True,
        "messages": [],
        "ask_referral_code": True,
        "referral_code_prompt": "Please enter the referral code, or type 'SKIP' if you don't have one:"
    })


@router.put('/first-time-greeting')
async def update_first_time_greeting(
    greeting_config: dict,
    current_user: dict = Depends(get_current_admin)
):
    """
    Update first-time greeting messages.
    
    Format:
    {
        "enabled": true,
        "messages": [
            {"order": 1, "message": "Welcome!", "delay_seconds": 0},
            {"order": 2, "message": "Do you have a referral code?", "delay_seconds": 2}
        ],
        "ask_referral_code": true,
        "referral_code_prompt": "Enter referral code or type SKIP:"
    }
    """
    db = await get_database()
    
    # Validate messages if provided
    if 'messages' in greeting_config:
        messages = greeting_config['messages']
        if not isinstance(messages, list):
            raise HTTPException(status_code=400, detail='messages must be a list')
        
        # Sort by order
        messages = sorted(messages, key=lambda x: x.get('order', 0))
        
        # Validate each message
        for msg in messages:
            if 'message' not in msg or not msg['message'].strip():
                raise HTTPException(status_code=400, detail='Each message must have non-empty "message" field')
            if 'order' not in msg:
                msg['order'] = messages.index(msg) + 1
            if 'delay_seconds' not in msg:
                msg['delay_seconds'] = 1
        
        greeting_config['messages'] = messages
    
    # Get current settings and merge
    settings = await get_global_settings(db)
    current_greeting = settings.get('first_time_greeting', {})
    current_greeting.update(greeting_config)
    
    await db.global_settings.update_one(
        {'_id': 'global'},
        {
            '$set': {
                'first_time_greeting': current_greeting,
                'updated_at': get_current_utc_iso(),
                'updated_by': current_user['id']
            }
        },
        upsert=True
    )
    
    invalidate_settings_cache()
    await log_settings_change(db, current_user['id'], 'first_time_greeting_update', greeting_config)
    
    return {'message': 'First-time greeting updated', 'greeting': current_greeting}


@router.post('/first-time-greeting/messages')
async def add_greeting_message(
    message: dict,
    current_user: dict = Depends(get_current_admin)
):
    """Add a new greeting message."""
    db = await get_database()
    
    if 'message' not in message or not message['message'].strip():
        raise HTTPException(status_code=400, detail='message field is required')
    
    settings = await get_global_settings(db)
    greeting = settings.get('first_time_greeting', {'messages': []})
    messages = greeting.get('messages', [])
    
    # Auto-assign order
    max_order = max([m.get('order', 0) for m in messages], default=0)
    new_message = {
        'order': message.get('order', max_order + 1),
        'message': message['message'].strip(),
        'delay_seconds': message.get('delay_seconds', 1)
    }
    
    messages.append(new_message)
    messages = sorted(messages, key=lambda x: x.get('order', 0))
    
    greeting['messages'] = messages
    
    await db.global_settings.update_one(
        {'_id': 'global'},
        {
            '$set': {
                'first_time_greeting': greeting,
                'updated_at': get_current_utc_iso(),
                'updated_by': current_user['id']
            }
        },
        upsert=True
    )
    
    invalidate_settings_cache()
    await log_settings_change(db, current_user['id'], 'greeting_message_add', new_message)
    
    return {'message': 'Greeting message added', 'messages': messages}


@router.delete('/first-time-greeting/messages/{order}')
async def delete_greeting_message(
    order: int,
    current_user: dict = Depends(get_current_admin)
):
    """Delete a greeting message by order."""
    db = await get_database()
    
    settings = await get_global_settings(db)
    greeting = settings.get('first_time_greeting', {'messages': []})
    messages = greeting.get('messages', [])
    
    new_messages = [m for m in messages if m.get('order') != order]
    
    if len(new_messages) == len(messages):
        raise HTTPException(status_code=404, detail='Message not found')
    
    # Re-order
    new_messages = sorted(new_messages, key=lambda x: x.get('order', 0))
    for i, m in enumerate(new_messages):
        m['order'] = i + 1
    
    greeting['messages'] = new_messages
    
    await db.global_settings.update_one(
        {'_id': 'global'},
        {
            '$set': {
                'first_time_greeting': greeting,
                'updated_at': get_current_utc_iso(),
                'updated_by': current_user['id']
            }
        },
        upsert=True
    )
    
    invalidate_settings_cache()
    await log_settings_change(db, current_user['id'], 'greeting_message_delete', {'order': order})
    
    return {'message': 'Greeting message deleted', 'messages': new_messages}
