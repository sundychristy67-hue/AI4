import uuid
import random
import string
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

def generate_id() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())

def generate_referral_code(length: int = 8) -> str:
    """Generate a random alphanumeric referral code."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def get_current_utc_iso() -> str:
    """Get current UTC timestamp as ISO string."""
    return datetime.now(timezone.utc).isoformat()

def get_current_utc() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)

def mask_credential(credential: str) -> str:
    """Mask a credential showing only first 2 and last 2 characters."""
    if not credential or len(credential) < 5:
        return '***'
    return f"{credential[:2]}{'*' * (len(credential) - 4)}{credential[-2:]}"

def row_to_dict(row) -> Optional[Dict]:
    """Convert asyncpg Record to dictionary."""
    if row is None:
        return None
    return dict(row)

def rows_to_list(rows) -> List[Dict]:
    """Convert list of asyncpg Records to list of dictionaries."""
    return [dict(row) for row in rows] if rows else []

def serialize_datetime(obj):
    """JSON serializer for datetime objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

# ==================== SETTINGS CACHE ====================

_settings_cache = {
    "data": None,
    "fetched_at": None,
    "ttl_seconds": 60  # Cache for 60 seconds
}

async def get_global_settings(pool) -> Dict[str, Any]:
    """
    Get global settings from database with caching.
    Returns default settings if not found.
    """
    from database import fetch_one
    
    now = datetime.now(timezone.utc)
    
    # Check cache
    if _settings_cache["data"] and _settings_cache["fetched_at"]:
        age = (now - _settings_cache["fetched_at"]).total_seconds()
        if age < _settings_cache["ttl_seconds"]:
            return _settings_cache["data"]
    
    # Fetch from database
    row = await fetch_one(
        "SELECT * FROM global_settings WHERE id = 'global'"
    )
    
    if not row:
        # Return defaults
        settings = get_default_settings()
    else:
        settings = row_to_dict(row)
        # Parse JSONB fields
        for field in ['referral_tier_config', 'bonus_rules', 'anti_fraud', 
                      'active_referral_criteria', 'first_time_greeting', 'telegram_config']:
            if field in settings and settings[field]:
                if isinstance(settings[field], str):
                    settings[field] = json.loads(settings[field])
    
    # Update cache
    _settings_cache["data"] = settings
    _settings_cache["fetched_at"] = now
    
    return settings

def invalidate_settings_cache():
    """Invalidate the settings cache to force refresh."""
    _settings_cache["data"] = None
    _settings_cache["fetched_at"] = None

def get_default_settings() -> Dict[str, Any]:
    """Get default settings structure."""
    return {
        "automation_enabled": True,
        "withdrawals_enabled": True,
        "bonus_system_enabled": True,
        "referral_system_enabled": True,
        "min_withdrawal_amount": 20.0,
        "max_withdrawal_amount": 10000.0,
        "withdrawal_fee_percentage": 0.0,
        "referral_tier_config": {
            "base_percentage": 5.0,
            "tiers": [
                {"tier_number": 0, "name": "Starter", "min_referrals": 0, "commission_percentage": 5.0},
                {"tier_number": 1, "name": "Bronze", "min_referrals": 10, "commission_percentage": 10.0},
                {"tier_number": 2, "name": "Silver", "min_referrals": 25, "commission_percentage": 15.0},
                {"tier_number": 3, "name": "Gold", "min_referrals": 50, "commission_percentage": 20.0},
                {"tier_number": 4, "name": "Platinum", "min_referrals": 100, "commission_percentage": 25.0},
                {"tier_number": 5, "name": "Diamond", "min_referrals": 200, "commission_percentage": 30.0},
            ]
        },
        "bonus_rules": {
            "enabled": True,
            "milestones": [
                {"milestone_number": 1, "referrals_required": 5, "bonus_amount": 5.0, "bonus_type": "bonus", "description": "First milestone bonus"},
                {"milestone_number": 2, "referrals_required": 10, "bonus_amount": 2.0, "bonus_type": "bonus", "description": "10 referrals bonus"},
                {"milestone_number": 3, "referrals_required": 15, "bonus_amount": 2.0, "bonus_type": "bonus", "description": "15 referrals bonus"},
                {"milestone_number": 4, "referrals_required": 20, "bonus_amount": 3.0, "bonus_type": "bonus", "description": "20 referrals bonus"},
                {"milestone_number": 5, "referrals_required": 30, "bonus_amount": 5.0, "bonus_type": "bonus", "description": "30 referrals bonus"},
                {"milestone_number": 6, "referrals_required": 50, "bonus_amount": 10.0, "bonus_type": "bonus", "description": "50 referrals bonus"},
            ],
            "use_legacy_mode": False
        },
        "anti_fraud": {
            "enabled": True,
            "max_referrals_per_ip": 3,
            "ip_cooldown_hours": 24,
            "min_account_age_hours": 1,
            "min_deposit_for_valid_referral": 10.0,
            "device_fingerprint_enabled": False,
            "max_referrals_per_device": 2,
            "flag_same_ip_referrals": True,
            "flag_rapid_signups": True,
            "rapid_signup_threshold_minutes": 5,
            "auto_flag_suspicious": True,
            "auto_reject_fraud": False
        },
        "active_referral_criteria": {
            "min_deposits_required": 1,
            "min_total_deposit_amount": 10.0,
            "activity_window_days": 30,
            "require_recent_activity": True
        },
        "first_time_greeting": {
            "enabled": True,
            "messages": [
                {
                    "order": 1,
                    "message": "👋 Welcome to our Gaming Platform!",
                    "delay_seconds": 0
                },
                {
                    "order": 2,
                    "message": "🎮 I'm here to help you get started. Do you have a referral code from a friend?",
                    "delay_seconds": 2
                },
                {
                    "order": 3,
                    "message": "If yes, please type your referral code now. If not, just type 'NO' or 'SKIP' to continue.",
                    "delay_seconds": 1
                }
            ],
            "ask_referral_code": True,
            "referral_code_prompt": "Please enter the referral code, or type 'SKIP' if you don't have one:"
        }
    }

# ==================== BONUS CALCULATION ====================

# Legacy defaults (used if DB not available)
BONUS_RULES = {
    "first_milestone": 5,
    "first_milestone_bonus": 5.0,
    "subsequent_block_size": 5,
    "subsequent_bonus": 2.0
}

async def calculate_referral_bonus_async(pool, valid_referral_count: int, already_claimed_milestones: list = None) -> Dict[str, Any]:
    """
    Calculate referral bonus based on valid referral count using DB settings.
    Uses milestone-based system from global settings.
    """
    if already_claimed_milestones is None:
        already_claimed_milestones = []
    
    settings = await get_global_settings(pool)
    bonus_rules = settings.get("bonus_rules", {})
    
    if not bonus_rules.get("enabled", True):
        return {
            "total_bonus_eligible": 0,
            "unclaimed_bonus": 0,
            "next_milestone": None,
            "milestones_reached": [],
            "milestones_unclaimed": []
        }
    
    milestones = bonus_rules.get("milestones", [])
    milestones = sorted(milestones, key=lambda x: x.get("referrals_required", 0))
    
    total_bonus = 0.0
    milestones_reached = []
    milestones_unclaimed = []
    
    for milestone in milestones:
        required = milestone.get("referrals_required", 0)
        if valid_referral_count >= required:
            milestones_reached.append(milestone)
            total_bonus += milestone.get("bonus_amount", 0)
            
            # Check if unclaimed
            if milestone.get("milestone_number") not in already_claimed_milestones:
                milestones_unclaimed.append(milestone)
    
    unclaimed_bonus = sum(m.get("bonus_amount", 0) for m in milestones_unclaimed)
    
    # Find next milestone
    next_milestone = None
    for milestone in milestones:
        if valid_referral_count < milestone.get("referrals_required", 0):
            next_milestone = milestone
            break
    
    return {
        "total_bonus_eligible": total_bonus,
        "unclaimed_bonus": unclaimed_bonus,
        "next_milestone": next_milestone,
        "milestones_reached": milestones_reached,
        "milestones_unclaimed": milestones_unclaimed,
        "referrals_until_next": (next_milestone.get("referrals_required", 0) - valid_referral_count) if next_milestone else 0
    }

def calculate_referral_bonus(valid_referral_count: int, already_claimed_bonuses: int = 0) -> Dict[str, Any]:
    """
    Legacy synchronous bonus calculation (uses hardcoded values).
    For backward compatibility - prefer calculate_referral_bonus_async.
    """
    total_bonus = 0.0
    bonus_count = 0
    
    if valid_referral_count >= BONUS_RULES["first_milestone"]:
        total_bonus += BONUS_RULES["first_milestone_bonus"]
        bonus_count += 1
        
        remaining = valid_referral_count - BONUS_RULES["first_milestone"]
        additional_blocks = remaining // BONUS_RULES["subsequent_block_size"]
        total_bonus += additional_blocks * BONUS_RULES["subsequent_bonus"]
        bonus_count += additional_blocks
    
    unclaimed_bonus = total_bonus - (already_claimed_bonuses * BONUS_RULES["subsequent_bonus"])
    if already_claimed_bonuses == 0 and total_bonus > 0:
        unclaimed_bonus = total_bonus
    
    if valid_referral_count < BONUS_RULES["first_milestone"]:
        next_bonus_at = BONUS_RULES["first_milestone"]
        next_bonus_amount = BONUS_RULES["first_milestone_bonus"]
    else:
        remaining = valid_referral_count - BONUS_RULES["first_milestone"]
        current_block = remaining // BONUS_RULES["subsequent_block_size"]
        next_bonus_at = BONUS_RULES["first_milestone"] + ((current_block + 1) * BONUS_RULES["subsequent_block_size"])
        next_bonus_amount = BONUS_RULES["subsequent_bonus"]
    
    return {
        "total_bonus_eligible": total_bonus,
        "bonus_count": bonus_count,
        "unclaimed_bonus": max(0, unclaimed_bonus),
        "next_bonus_at": next_bonus_at,
        "next_bonus_amount": next_bonus_amount,
        "referrals_until_next": next_bonus_at - valid_referral_count
    }

async def calculate_referral_tier_async(pool, valid_referral_count: int) -> Dict[str, Any]:
    """
    Calculate referral tier using DB settings.
    """
    settings = await get_global_settings(pool)
    tier_config = settings.get("referral_tier_config", {})
    tiers = tier_config.get("tiers", [])
    
    # Sort by min_referrals
    tiers = sorted(tiers, key=lambda x: x.get("min_referrals", 0))
    
    current_tier = tiers[0] if tiers else {"tier_number": 0, "name": "Starter", "commission_percentage": 5.0}
    next_tier = None
    
    for i, tier in enumerate(tiers):
        if valid_referral_count >= tier.get("min_referrals", 0):
            current_tier = tier
            if i + 1 < len(tiers):
                next_tier = tiers[i + 1]
            else:
                next_tier = None
    
    # Calculate progress to next tier
    if next_tier:
        current_min = current_tier.get("min_referrals", 0)
        next_min = next_tier.get("min_referrals", 0)
        progress = ((valid_referral_count - current_min) / (next_min - current_min)) * 100 if next_min > current_min else 100
    else:
        progress = 100
    
    return {
        "tier": current_tier.get("tier_number", 0),
        "tier_name": current_tier.get("name", "Starter"),
        "percentage": current_tier.get("commission_percentage", 5.0),
        "next_tier": next_tier,
        "next_tier_at": next_tier.get("min_referrals") if next_tier else None,
        "progress_to_next": min(100, progress),
        "referrals_until_next_tier": (next_tier.get("min_referrals", 0) - valid_referral_count) if next_tier else 0
    }

def calculate_referral_tier(valid_referral_count: int) -> Dict[str, Any]:
    """
    Legacy synchronous tier calculation (uses hardcoded values).
    For backward compatibility - prefer calculate_referral_tier_async.
    """
    tier_thresholds = [5, 10, 20, 50]
    tier_percentages = [5.0, 6.0, 7.0, 8.0, 10.0]
    
    tier = 0
    for i, threshold in enumerate(tier_thresholds):
        if valid_referral_count >= threshold:
            tier = i + 1
    
    percentage = tier_percentages[tier] if tier < len(tier_percentages) else tier_percentages[-1]
    
    if tier < len(tier_thresholds):
        next_tier_at = tier_thresholds[tier]
        progress = (valid_referral_count / next_tier_at) * 100 if next_tier_at > 0 else 100
    else:
        next_tier_at = None
        progress = 100
    
    return {
        "tier": tier,
        "percentage": percentage,
        "next_tier_at": next_tier_at,
        "progress_to_next": min(100, progress),
        "referrals_until_next_tier": (next_tier_at - valid_referral_count) if next_tier_at else 0
    }

# ==================== ANTI-FRAUD CHECKS ====================

async def check_referral_fraud(pool, referrer_client_id: str, referred_client_id: str, ip_address: str = None) -> Dict[str, Any]:
    """
    Check for potential referral fraud based on anti-fraud settings.
    Returns dict with 'is_suspicious', 'flags', and 'should_reject'.
    """
    from database import fetch_one
    
    settings = await get_global_settings(pool)
    anti_fraud = settings.get("anti_fraud", {})
    
    if not anti_fraud.get("enabled", True):
        return {"is_suspicious": False, "flags": [], "should_reject": False}
    
    flags = []
    
    # Check IP-based fraud
    if ip_address and anti_fraud.get("flag_same_ip_referrals", True):
        referrer = await fetch_one(
            "SELECT last_ip FROM clients WHERE client_id = $1", referrer_client_id
        )
        referred = await fetch_one(
            "SELECT last_ip, created_at FROM clients WHERE client_id = $1", referred_client_id
        )
        
        if referrer and referred:
            referrer_ip = referrer['last_ip']
            referred_ip = referred['last_ip'] or ip_address
            if referrer_ip and referred_ip and referrer_ip == referred_ip:
                flags.append("SAME_IP_AS_REFERRER")
    
    # Check rapid signups
    if anti_fraud.get("flag_rapid_signups", True):
        threshold_minutes = anti_fraud.get("rapid_signup_threshold_minutes", 5)
        referred = await fetch_one(
            "SELECT created_at FROM clients WHERE client_id = $1", referred_client_id
        )
        if referred and referred['created_at']:
            created_dt = referred['created_at']
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)
            age_minutes = (datetime.now(timezone.utc) - created_dt).total_seconds() / 60
            if age_minutes < threshold_minutes:
                flags.append("RAPID_SIGNUP")
    
    # Check minimum account age
    min_age_hours = anti_fraud.get("min_account_age_hours", 1)
    referred = await fetch_one(
        "SELECT created_at FROM clients WHERE client_id = $1", referred_client_id
    )
    if referred and referred['created_at']:
        created_dt = referred['created_at']
        if created_dt.tzinfo is None:
            created_dt = created_dt.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - created_dt).total_seconds() / 3600
        if age_hours < min_age_hours:
            flags.append("ACCOUNT_TOO_NEW")
    
    is_suspicious = len(flags) > 0
    should_reject = is_suspicious and anti_fraud.get("auto_reject_fraud", False)
    
    return {
        "is_suspicious": is_suspicious,
        "flags": flags,
        "should_reject": should_reject,
        "auto_flag": anti_fraud.get("auto_flag_suspicious", True)
    }

# ==================== WALLET CALCULATIONS ====================

async def calculate_wallet_balances(pool, client_id: str) -> Dict[str, float]:
    """
    Calculate real and bonus wallet balances from ledger.
    
    Real Wallet: IN - OUT - REAL_LOAD + REFERRAL_EARN + ADJUST
    Bonus Wallet: BONUS_EARN - BONUS_LOAD + BONUS_ADJUST
    """
    from database import fetch_all
    
    # Get confirmed transaction totals by type
    rows = await fetch_all(
        """
        SELECT type, SUM(amount) as total 
        FROM ledger_transactions 
        WHERE client_id = $1 AND status = 'confirmed'
        GROUP BY type
        """,
        client_id
    )
    
    totals = {row['type']: row['total'] or 0 for row in rows}
    
    # Real wallet calculation
    total_in = totals.get('IN', 0)
    total_out = totals.get('OUT', 0)
    real_load = totals.get('REAL_LOAD', 0)
    referral_earn = totals.get('REFERRAL_EARN', 0)
    adjust = totals.get('ADJUST', 0)
    
    real_balance = total_in - total_out - real_load + referral_earn + adjust
    
    # Bonus wallet calculation
    bonus_earn = totals.get('BONUS_EARN', 0)
    bonus_load = totals.get('BONUS_LOAD', 0)
    bonus_adjust = totals.get('BONUS_ADJUST', 0)
    
    bonus_balance = bonus_earn - bonus_load + bonus_adjust
    
    # Pending amounts
    pending_rows = await fetch_all(
        """
        SELECT type, SUM(amount) as total 
        FROM ledger_transactions 
        WHERE client_id = $1 AND status = 'pending'
        GROUP BY type
        """,
        client_id
    )
    pending_totals = {row['type']: row['total'] or 0 for row in pending_rows}
    
    return {
        'real_balance': max(0, real_balance),
        'bonus_balance': max(0, bonus_balance),
        'total_in': total_in,
        'total_out': total_out,
        'total_real_loaded': real_load,
        'total_bonus_loaded': bonus_load,
        'total_bonus_earned': bonus_earn,
        'referral_earnings': referral_earn,
        'pending_in': pending_totals.get('IN', 0),
        'pending_out': pending_totals.get('OUT', 0)
    }

# ==================== REFERRAL APPLICATION ====================

async def apply_referral_code(pool, client_id: str, referral_code: str) -> dict:
    """
    Apply a referral code to a client.
    Returns {'success': bool, 'message': str}
    """
    from database import fetch_one, execute
    
    referral_code = referral_code.upper().strip()
    
    # Get the client
    client = await fetch_one(
        "SELECT * FROM clients WHERE client_id = $1", client_id
    )
    if not client:
        return {'success': False, 'message': 'Client not found'}
    
    client = row_to_dict(client)
    
    # Check if referral already locked
    if client.get('referral_locked'):
        return {'success': False, 'message': 'Referral code cannot be applied after first deposit'}
    
    # Check if already has a referral
    if client.get('referred_by_code'):
        return {'success': False, 'message': 'Already have a referral code applied'}
    
    # Find the referrer
    referrer = await fetch_one(
        "SELECT * FROM clients WHERE referral_code = $1", referral_code
    )
    if not referrer:
        return {'success': False, 'message': 'Invalid referral code'}
    
    referrer = row_to_dict(referrer)
    
    # Cannot refer yourself
    if referrer['client_id'] == client_id:
        return {'success': False, 'message': 'Cannot use your own referral code'}
    
    # Check for circular referrals (A→B→A)
    if referrer.get('referred_by_code'):
        referrer_referrer = await fetch_one(
            "SELECT client_id FROM clients WHERE referral_code = $1",
            referrer['referred_by_code']
        )
        if referrer_referrer and referrer_referrer['client_id'] == client_id:
            return {'success': False, 'message': 'Circular referrals are not allowed'}
    
    # Apply the referral
    await execute(
        "UPDATE clients SET referred_by_code = $1 WHERE client_id = $2",
        referral_code, client_id
    )
    
    # Create referral record
    referral_id = generate_id()
    try:
        await execute(
            """
            INSERT INTO client_referrals (id, referrer_client_id, referred_client_id, status, total_deposits, created_at)
            VALUES ($1, $2, $3, 'pending', 0, $4)
            """,
            referral_id, referrer['client_id'], client_id, get_current_utc()
        )
    except Exception:
        pass  # May already exist
    
    # Update referrer's referral count
    await execute(
        "UPDATE clients SET referral_count = referral_count + 1 WHERE client_id = $1",
        referrer['client_id']
    )
    
    return {'success': True, 'message': 'Referral code applied successfully'}

async def process_referral_on_deposit(pool, client_id: str, deposit_amount: float) -> Dict[str, Any]:
    """
    Process referral-related actions when a client makes a deposit.
    """
    from database import fetch_one, execute
    
    result = {
        'referral_locked': False,
        'referral_activated': False,
        'referrer_earned': 0,
        'bonus_credited': 0
    }
    
    client = await fetch_one(
        "SELECT * FROM clients WHERE client_id = $1", client_id
    )
    if not client:
        return result
    
    client = row_to_dict(client)
    
    # Lock referral application after first deposit
    if not client.get('referral_locked'):
        await execute(
            "UPDATE clients SET referral_locked = TRUE WHERE client_id = $1",
            client_id
        )
        result['referral_locked'] = True
    
    # Check if client has a referrer
    if client.get('referred_by_code'):
        referrer = await fetch_one(
            "SELECT * FROM clients WHERE referral_code = $1",
            client['referred_by_code']
        )
        
        if referrer:
            referrer = row_to_dict(referrer)
            
            # Get referral record
            referral = await fetch_one(
                "SELECT * FROM client_referrals WHERE referred_client_id = $1",
                client_id
            )
            
            if referral:
                referral = row_to_dict(referral)
                
                # Update referral status to valid on first deposit
                if referral.get('status') == 'pending':
                    await execute(
                        "UPDATE client_referrals SET status = 'valid' WHERE referred_client_id = $1",
                        client_id
                    )
                    result['referral_activated'] = True
                    
                    # Increment valid referral count
                    await execute(
                        "UPDATE clients SET valid_referral_count = valid_referral_count + 1 WHERE client_id = $1",
                        referrer['client_id']
                    )
                    
                    # Check and process referral bonuses for referrer
                    updated_referrer = await fetch_one(
                        "SELECT * FROM clients WHERE client_id = $1",
                        referrer['client_id']
                    )
                    
                    if updated_referrer:
                        updated_referrer = row_to_dict(updated_referrer)
                        bonus_info = calculate_referral_bonus(
                            updated_referrer.get('valid_referral_count', 0),
                            updated_referrer.get('bonus_claims', 0)
                        )
                        
                        if bonus_info['unclaimed_bonus'] > 0:
                            # Credit bonus to referrer's bonus wallet
                            bonus_tx_id = generate_id()
                            await execute(
                                """
                                INSERT INTO ledger_transactions 
                                (transaction_id, client_id, type, amount, wallet_type, status, source, reason, created_at, confirmed_at)
                                VALUES ($1, $2, 'BONUS_EARN', $3, 'bonus', 'confirmed', 'referral_bonus', $4, $5, $5)
                                """,
                                bonus_tx_id, referrer['client_id'], bonus_info['unclaimed_bonus'],
                                f"Referral milestone bonus ({updated_referrer.get('valid_referral_count', 0)} valid referrals)",
                                get_current_utc()
                            )
                            
                            # Update bonus claims count
                            await execute(
                                "UPDATE clients SET bonus_claims = bonus_claims + 1 WHERE client_id = $1",
                                referrer['client_id']
                            )
                            
                            result['bonus_credited'] = bonus_info['unclaimed_bonus']
                
                # Update total deposits in referral record
                await execute(
                    "UPDATE client_referrals SET total_deposits = total_deposits + $1 WHERE referred_client_id = $2",
                    deposit_amount, client_id
                )
                
                # Calculate and credit referrer earnings (percentage of deposit)
                tier_info = calculate_referral_tier(referrer.get('valid_referral_count', 0))
                earnings = deposit_amount * (tier_info['percentage'] / 100)
                
                if earnings > 0:
                    earnings_tx_id = generate_id()
                    await execute(
                        """
                        INSERT INTO ledger_transactions 
                        (transaction_id, client_id, type, amount, wallet_type, status, source, reason, metadata, created_at, confirmed_at)
                        VALUES ($1, $2, 'REFERRAL_EARN', $3, 'real', 'confirmed', 'referral', $4, $5, $6, $6)
                        """,
                        earnings_tx_id, referrer['client_id'], earnings,
                        f"Referral earnings from {client.get('display_name', 'client')} deposit",
                        json.dumps({
                            'referred_client_id': client_id,
                            'deposit_amount': deposit_amount,
                            'percentage': tier_info['percentage']
                        }),
                        get_current_utc()
                    )
                    result['referrer_earned'] = earnings
    
    return result
