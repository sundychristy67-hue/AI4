"""
Admin Settings Routes - PostgreSQL Version
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, List
import json
from auth import get_current_admin
from database import fetch_one, execute, row_to_dict
from utils import get_current_utc, get_current_utc_iso, get_default_settings, get_global_settings, invalidate_settings_cache
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix='/admin/settings', tags=['Admin Settings'])


async def log_settings_change(admin_id: str, change_type: str, details: dict):
    """Log settings changes for audit."""
    from utils import generate_id
    log_id = generate_id()
    await execute(
        """
        INSERT INTO audit_logs (id, admin_id, action, entity_type, entity_id, details, timestamp)
        VALUES ($1, $2, $3, 'settings', 'global', $4, $5)
        """,
        log_id, admin_id, f'settings_{change_type}', json.dumps(details), get_current_utc()
    )


async def get_or_create_settings():
    """Get settings or create with defaults."""
    from database import get_pool
    pool = await get_pool()
    
    row = await fetch_one("SELECT * FROM global_settings WHERE id = 'global'")
    if row:
        settings = row_to_dict(row)
        # Parse JSONB fields if they're strings
        for field in ['referral_tier_config', 'bonus_rules', 'anti_fraud', 
                      'active_referral_criteria', 'first_time_greeting', 'telegram_config']:
            if field in settings and settings[field] and isinstance(settings[field], str):
                settings[field] = json.loads(settings[field])
        return settings
    
    # Create with defaults
    defaults = get_default_settings()
    await execute(
        """
        INSERT INTO global_settings (id, referral_tier_config, bonus_rules, anti_fraud, active_referral_criteria, first_time_greeting)
        VALUES ('global', $1, $2, $3, $4, $5)
        """,
        json.dumps(defaults['referral_tier_config']),
        json.dumps(defaults['bonus_rules']),
        json.dumps(defaults['anti_fraud']),
        json.dumps(defaults['active_referral_criteria']),
        json.dumps(defaults['first_time_greeting'])
    )
    return defaults


# ==================== GET SETTINGS ====================

@router.get('')
async def get_all_settings(current_user: dict = Depends(get_current_admin)):
    """Get all global settings."""
    from database import get_pool
    pool = await get_pool()
    return await get_global_settings(pool)


@router.get('/referral-tiers')
async def get_referral_tiers(current_user: dict = Depends(get_current_admin)):
    """Get referral tier configuration."""
    from database import get_pool
    pool = await get_pool()
    settings = await get_global_settings(pool)
    return settings.get('referral_tier_config', {})


@router.get('/bonus-milestones')
async def get_bonus_milestones(current_user: dict = Depends(get_current_admin)):
    """Get bonus milestones configuration."""
    from database import get_pool
    pool = await get_pool()
    settings = await get_global_settings(pool)
    return settings.get('bonus_rules', {})


@router.get('/anti-fraud')
async def get_anti_fraud_settings(current_user: dict = Depends(get_current_admin)):
    """Get anti-fraud configuration."""
    from database import get_pool
    pool = await get_pool()
    settings = await get_global_settings(pool)
    return settings.get('anti_fraud', {})


# ==================== UPDATE GLOBAL SETTINGS ====================

@router.put('')
async def update_global_settings(updates: dict, current_user: dict = Depends(get_current_admin)):
    """Update global feature toggles and basic settings."""
    allowed_fields = [
        'automation_enabled', 'withdrawals_enabled', 'bonus_system_enabled',
        'referral_system_enabled', 'min_withdrawal_amount', 'max_withdrawal_amount',
        'withdrawal_fee_percentage'
    ]
    
    update_parts = []
    params = []
    param_idx = 1
    
    for field in allowed_fields:
        if field in updates:
            update_parts.append(f"{field} = ${param_idx}")
            params.append(updates[field])
            param_idx += 1
    
    if not update_parts:
        raise HTTPException(status_code=400, detail='No valid fields to update')
    
    update_parts.append(f"updated_at = ${param_idx}")
    params.append(get_current_utc())
    param_idx += 1
    
    update_parts.append(f"updated_by = ${param_idx}")
    params.append(current_user['id'])
    
    # Ensure record exists
    await get_or_create_settings()
    
    await execute(f"UPDATE global_settings SET {', '.join(update_parts)} WHERE id = 'global'", *params)
    
    invalidate_settings_cache()
    await log_settings_change(current_user['id'], 'global_update', {k: updates[k] for k in allowed_fields if k in updates})
    
    return {'message': 'Settings updated successfully', 'updated_fields': [f for f in allowed_fields if f in updates]}


# ==================== REFERRAL TIERS ====================

@router.put('/referral-tiers')
async def update_referral_tiers(tiers: List[dict], current_user: dict = Depends(get_current_admin)):
    """Replace all referral tiers with new configuration."""
    if not tiers:
        raise HTTPException(status_code=400, detail='At least one tier is required')
    
    has_base_tier = any(t.get('min_referrals', -1) == 0 for t in tiers)
    if not has_base_tier:
        raise HTTPException(status_code=400, detail='Must have a base tier with min_referrals=0')
    
    for tier in tiers:
        if 'commission_percentage' not in tier or tier['commission_percentage'] < 0:
            raise HTTPException(status_code=400, detail='Each tier must have a valid commission_percentage >= 0')
        if 'min_referrals' not in tier or tier['min_referrals'] < 0:
            raise HTTPException(status_code=400, detail='Each tier must have a valid min_referrals >= 0')
    
    tiers = sorted(tiers, key=lambda x: x.get('min_referrals', 0))
    for i, tier in enumerate(tiers):
        tier['tier_number'] = i
    
    tier_config = {
        'base_percentage': tiers[0].get('commission_percentage', 5.0),
        'tiers': tiers
    }
    
    await get_or_create_settings()
    await execute(
        "UPDATE global_settings SET referral_tier_config = $1, updated_at = $2, updated_by = $3 WHERE id = 'global'",
        json.dumps(tier_config), get_current_utc(), current_user['id']
    )
    
    invalidate_settings_cache()
    await log_settings_change(current_user['id'], 'referral_tiers_update', {'tiers_count': len(tiers)})
    
    return {'message': 'Referral tiers updated successfully', 'tiers': tiers}


# ==================== BONUS MILESTONES ====================

@router.put('/bonus-milestones')
async def update_bonus_milestones(milestones: List[dict], current_user: dict = Depends(get_current_admin)):
    """Replace all bonus milestones with new configuration."""
    for milestone in milestones:
        if 'referrals_required' not in milestone or milestone['referrals_required'] < 1:
            raise HTTPException(status_code=400, detail='Each milestone must have referrals_required >= 1')
        if 'bonus_amount' not in milestone or milestone['bonus_amount'] <= 0:
            raise HTTPException(status_code=400, detail='Each milestone must have bonus_amount > 0')
    
    milestones = sorted(milestones, key=lambda x: x.get('referrals_required', 0))
    for i, milestone in enumerate(milestones):
        milestone['milestone_number'] = i + 1
        if 'bonus_type' not in milestone:
            milestone['bonus_type'] = 'bonus'
        if 'description' not in milestone:
            milestone['description'] = f"{milestone['referrals_required']} referrals bonus"
    
    from database import get_pool
    pool = await get_pool()
    settings = await get_global_settings(pool)
    bonus_rules = settings.get('bonus_rules', {'enabled': True})
    bonus_rules['milestones'] = milestones
    
    await get_or_create_settings()
    await execute(
        "UPDATE global_settings SET bonus_rules = $1, updated_at = $2, updated_by = $3 WHERE id = 'global'",
        json.dumps(bonus_rules), get_current_utc(), current_user['id']
    )
    
    invalidate_settings_cache()
    await log_settings_change(current_user['id'], 'bonus_milestones_update', {'count': len(milestones)})
    
    return {'message': 'Bonus milestones updated successfully', 'milestones': milestones}


@router.put('/bonus-milestones/toggle')
async def toggle_bonus_system(enabled: bool, current_user: dict = Depends(get_current_admin)):
    """Enable or disable the bonus system."""
    from database import get_pool
    pool = await get_pool()
    settings = await get_global_settings(pool)
    
    bonus_rules = settings.get('bonus_rules', {'milestones': []})
    bonus_rules['enabled'] = enabled
    
    await get_or_create_settings()
    await execute(
        "UPDATE global_settings SET bonus_rules = $1, bonus_system_enabled = $2, updated_at = $3, updated_by = $4 WHERE id = 'global'",
        json.dumps(bonus_rules), enabled, get_current_utc(), current_user['id']
    )
    
    invalidate_settings_cache()
    await log_settings_change(current_user['id'], 'bonus_system_toggle', {'enabled': enabled})
    
    return {'message': f'Bonus system {"enabled" if enabled else "disabled"}', 'enabled': enabled}


# ==================== ANTI-FRAUD SETTINGS ====================

@router.put('/anti-fraud')
async def update_anti_fraud_settings(updates: dict, current_user: dict = Depends(get_current_admin)):
    """Update anti-fraud detection settings."""
    from database import get_pool
    pool = await get_pool()
    settings = await get_global_settings(pool)
    
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
    
    await get_or_create_settings()
    await execute(
        "UPDATE global_settings SET anti_fraud = $1, updated_at = $2, updated_by = $3 WHERE id = 'global'",
        json.dumps(anti_fraud), get_current_utc(), current_user['id']
    )
    
    invalidate_settings_cache()
    await log_settings_change(current_user['id'], 'anti_fraud_update', updates)
    
    return {'message': 'Anti-fraud settings updated successfully', 'anti_fraud': anti_fraud}


# ==================== RESET TO DEFAULTS ====================

@router.post('/reset-defaults')
async def reset_to_defaults(section: Optional[str] = None, current_user: dict = Depends(get_current_admin)):
    """Reset settings to defaults."""
    defaults = get_default_settings()
    
    await get_or_create_settings()
    
    if section is None or section == 'all':
        await execute(
            """
            UPDATE global_settings SET 
                referral_tier_config = $1, bonus_rules = $2, anti_fraud = $3,
                active_referral_criteria = $4, first_time_greeting = $5,
                updated_at = $6, updated_by = $7
            WHERE id = 'global'
            """,
            json.dumps(defaults['referral_tier_config']),
            json.dumps(defaults['bonus_rules']),
            json.dumps(defaults['anti_fraud']),
            json.dumps(defaults['active_referral_criteria']),
            json.dumps(defaults['first_time_greeting']),
            get_current_utc(), current_user['id']
        )
    elif section == 'tiers':
        await execute(
            "UPDATE global_settings SET referral_tier_config = $1, updated_at = $2, updated_by = $3 WHERE id = 'global'",
            json.dumps(defaults['referral_tier_config']), get_current_utc(), current_user['id']
        )
    elif section == 'milestones':
        await execute(
            "UPDATE global_settings SET bonus_rules = $1, updated_at = $2, updated_by = $3 WHERE id = 'global'",
            json.dumps(defaults['bonus_rules']), get_current_utc(), current_user['id']
        )
    elif section == 'antifraud':
        await execute(
            "UPDATE global_settings SET anti_fraud = $1, updated_at = $2, updated_by = $3 WHERE id = 'global'",
            json.dumps(defaults['anti_fraud']), get_current_utc(), current_user['id']
        )
    else:
        raise HTTPException(status_code=400, detail='Invalid section. Use: all, tiers, milestones, antifraud')
    
    invalidate_settings_cache()
    await log_settings_change(current_user['id'], 'reset_defaults', {'section': section or 'all'})
    
    return {'message': f'Settings reset to defaults ({section or "all"})'}


# ==================== ACTIVE REFERRAL CRITERIA ====================

@router.get('/active-referral-criteria')
async def get_active_referral_criteria(current_user: dict = Depends(get_current_admin)):
    """Get active referral criteria configuration."""
    from database import get_pool
    pool = await get_pool()
    settings = await get_global_settings(pool)
    return settings.get('active_referral_criteria', {
        "min_deposits_required": 1,
        "min_total_deposit_amount": 10.0,
        "activity_window_days": 30,
        "require_recent_activity": True
    })


@router.put('/active-referral-criteria')
async def update_active_referral_criteria(criteria: dict, current_user: dict = Depends(get_current_admin)):
    """Update active referral criteria."""
    from database import get_pool
    pool = await get_pool()
    
    allowed_fields = [
        'min_deposits_required', 'min_total_deposit_amount', 
        'activity_window_days', 'require_recent_activity'
    ]
    
    valid_criteria = {k: v for k, v in criteria.items() if k in allowed_fields}
    
    if not valid_criteria:
        raise HTTPException(status_code=400, detail='No valid criteria fields provided')
    
    settings = await get_global_settings(pool)
    current_criteria = settings.get('active_referral_criteria', {})
    current_criteria.update(valid_criteria)
    
    await get_or_create_settings()
    await execute(
        "UPDATE global_settings SET active_referral_criteria = $1, updated_at = $2, updated_by = $3 WHERE id = 'global'",
        json.dumps(current_criteria), get_current_utc(), current_user['id']
    )
    
    invalidate_settings_cache()
    await log_settings_change(current_user['id'], 'active_referral_criteria_update', valid_criteria)
    
    return {'message': 'Active referral criteria updated', 'criteria': current_criteria}


# ==================== FIRST-TIME GREETING MESSAGES ====================

@router.get('/first-time-greeting')
async def get_first_time_greeting(current_user: dict = Depends(get_current_admin)):
    """Get first-time client greeting messages configuration."""
    from database import get_pool
    pool = await get_pool()
    settings = await get_global_settings(pool)
    return settings.get('first_time_greeting', {
        "enabled": True,
        "messages": [],
        "ask_referral_code": True,
        "referral_code_prompt": "Please enter the referral code, or type 'SKIP' if you don't have one:"
    })


@router.put('/first-time-greeting')
async def update_first_time_greeting(greeting_config: dict, current_user: dict = Depends(get_current_admin)):
    """Update first-time greeting messages."""
    from database import get_pool
    pool = await get_pool()
    
    if 'messages' in greeting_config:
        messages = greeting_config['messages']
        if not isinstance(messages, list):
            raise HTTPException(status_code=400, detail='messages must be a list')
        
        messages = sorted(messages, key=lambda x: x.get('order', 0))
        
        for msg in messages:
            if 'message' not in msg or not msg['message'].strip():
                raise HTTPException(status_code=400, detail='Each message must have non-empty "message" field')
            if 'order' not in msg:
                msg['order'] = messages.index(msg) + 1
            if 'delay_seconds' not in msg:
                msg['delay_seconds'] = 1
        
        greeting_config['messages'] = messages
    
    settings = await get_global_settings(pool)
    current_greeting = settings.get('first_time_greeting', {})
    current_greeting.update(greeting_config)
    
    await get_or_create_settings()
    await execute(
        "UPDATE global_settings SET first_time_greeting = $1, updated_at = $2, updated_by = $3 WHERE id = 'global'",
        json.dumps(current_greeting), get_current_utc(), current_user['id']
    )
    
    invalidate_settings_cache()
    await log_settings_change(current_user['id'], 'first_time_greeting_update', greeting_config)
    
    return {'message': 'First-time greeting updated', 'greeting': current_greeting}
