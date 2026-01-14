from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# ==================== ENUMS ====================

class UserRole(str, Enum):
    USER = 'user'
    ADMIN = 'admin'

class ClientStatus(str, Enum):
    ACTIVE = 'active'
    FROZEN = 'frozen'
    BANNED = 'banned'

class ReferralStatus(str, Enum):
    PENDING = 'pending'
    ACTIVE = 'active'
    SUSPECTED = 'suspected'
    VALID = 'valid'
    FRAUD = 'fraud'

class TransactionType(str, Enum):
    IN = 'IN'                      # Deposit to real wallet
    OUT = 'OUT'                    # Withdrawal from real wallet
    ADJUST = 'ADJUST'              # Manual adjustment (real wallet)
    REFERRAL_EARN = 'REFERRAL_EARN'  # Direct referral earnings (real wallet)
    REAL_LOAD = 'REAL_LOAD'        # Load from real wallet to game
    BONUS_EARN = 'BONUS_EARN'      # Bonus credited (to bonus wallet)
    BONUS_LOAD = 'BONUS_LOAD'      # Load from bonus wallet to game
    BONUS_ADJUST = 'BONUS_ADJUST'  # Manual bonus adjustment

class TransactionStatus(str, Enum):
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    REJECTED = 'rejected'

class TransactionSource(str, Enum):
    TELEGRAM_CASHIN = 'telegram_cashin'
    TELEGRAM_CASHOUT = 'telegram_cashout'
    TELEGRAM_LOAD = 'telegram_load'
    ADMIN_ADJUST = 'admin_adjust'
    REFERRAL = 'referral'
    REFERRAL_BONUS = 'referral_bonus'
    AUTOMATION = 'automation'
    PORTAL = 'portal'

class WalletType(str, Enum):
    REAL = 'real'
    BONUS = 'bonus'

class OrderType(str, Enum):
    CREATE = 'create'
    LOAD = 'load'
    REDEEM = 'redeem'

class OrderStatus(str, Enum):
    DRAFT = 'draft'
    PENDING_SCREENSHOT = 'pending_screenshot'
    PENDING_CONFIRMATION = 'pending_confirmation'
    PENDING_PAYOUT = 'pending_payout'
    CONFIRMED = 'confirmed'
    REJECTED = 'rejected'
    CANCELLED = 'cancelled'

class VisibilityLevel(str, Enum):
    HIDDEN = 'hidden'
    SUMMARY = 'summary'
    FULL = 'full'

# ==================== CLIENT MODELS ====================

class ClientCreate(BaseModel):
    chatwoot_contact_id: Optional[str] = None
    messenger_psid: Optional[str] = None
    display_name: Optional[str] = None

class ClientUpdate(BaseModel):
    display_name: Optional[str] = None
    status: Optional[ClientStatus] = None
    withdraw_locked: Optional[bool] = None
    load_locked: Optional[bool] = None
    bonus_locked: Optional[bool] = None
    visibility_level: Optional[VisibilityLevel] = None

class ClientPasswordSetup(BaseModel):
    """Request to set up password for client portal"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

class ClientPasswordLogin(BaseModel):
    """Client login with username/password"""
    username: str
    password: str

class ClientPasswordLoginResponse(BaseModel):
    """Response for client password login"""
    success: bool
    message: str
    client_id: Optional[str] = None
    access_token: Optional[str] = None
    display_name: Optional[str] = None

class ClientResponse(BaseModel):
    model_config = ConfigDict(extra='ignore')
    client_id: str
    chatwoot_contact_id: Optional[str] = None
    messenger_psid: Optional[str] = None
    display_name: Optional[str] = None
    status: ClientStatus = ClientStatus.ACTIVE
    withdraw_locked: bool = False
    load_locked: bool = False
    bonus_locked: bool = False
    referred_by_code: Optional[str] = None
    referral_code: Optional[str] = None
    referral_locked: bool = False
    referral_count: int = 0
    valid_referral_count: int = 0
    referral_tier: int = 0
    referral_percentage: float = 5.0
    visibility_level: VisibilityLevel = VisibilityLevel.FULL
    created_at: str
    last_active_at: Optional[str] = None

# ==================== WALLET MODELS ====================

class WalletSummary(BaseModel):
    real_balance: float = 0.0
    bonus_balance: float = 0.0
    total_in: float = 0.0
    total_out: float = 0.0
    total_real_loaded: float = 0.0
    total_bonus_loaded: float = 0.0
    total_bonus_earned: float = 0.0
    referral_earnings: float = 0.0
    pending_in: float = 0.0
    pending_out: float = 0.0

# ==================== PORTAL SESSION MODELS ====================

class PortalSessionCreate(BaseModel):
    chatwoot_contact_id: Optional[str] = None
    client_id: Optional[str] = None

class PortalSessionResponse(BaseModel):
    token: str
    portal_url: str
    expires_at: str
    client_id: str

class PortalValidateResponse(BaseModel):
    valid: bool
    client: Optional[ClientResponse] = None
    message: Optional[str] = None

# ==================== LEDGER/TRANSACTION MODELS ====================

class LedgerTransactionCreate(BaseModel):
    client_id: str
    type: TransactionType
    amount: float
    source: TransactionSource
    wallet_type: WalletType = WalletType.REAL
    order_id: Optional[str] = None
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    idempotency_key: Optional[str] = None

class LedgerTransactionResponse(BaseModel):
    model_config = ConfigDict(extra='ignore')
    transaction_id: str
    client_id: str
    type: TransactionType
    amount: float
    wallet_type: WalletType = WalletType.REAL
    status: TransactionStatus
    source: TransactionSource
    order_id: Optional[str] = None
    reason: Optional[str] = None
    idempotency_key: Optional[str] = None
    original_amount: Optional[float] = None
    created_at: str
    confirmed_at: Optional[str] = None
    confirmed_by: Optional[str] = None

class ClientFinancialSummary(BaseModel):
    client_id: str
    real_balance: float
    bonus_balance: float
    lifetime_total_in: float
    lifetime_total_out: float
    net_flow: float
    pending_in: float
    pending_out: float
    referral_earnings: float
    bonus_earnings: float

# ==================== LOAD TO GAME MODELS ====================

class LoadToGameRequest(BaseModel):
    game_id: str
    amount: float
    wallet_type: WalletType = WalletType.REAL

class LoadToGameResponse(BaseModel):
    order_id: str
    client_id: str
    game_id: str
    game_name: str
    amount: float
    wallet_type: WalletType
    status: OrderStatus
    message: str

# ==================== ORDER MODELS ====================

class OrderCreate(BaseModel):
    client_id: str
    order_type: OrderType
    game: str
    amount: float
    wallet_type: WalletType = WalletType.REAL
    username: Optional[str] = None
    password: Optional[str] = None
    payment_method: Optional[str] = None
    payout_tag: Optional[str] = None

class OrderResponse(BaseModel):
    model_config = ConfigDict(extra='ignore')
    order_id: str
    client_id: str
    order_type: OrderType
    game: str
    amount: float
    wallet_type: WalletType = WalletType.REAL
    original_amount: Optional[float] = None
    username: Optional[str] = None
    password: Optional[str] = None
    payment_method: Optional[str] = None
    payout_tag: Optional[str] = None
    status: OrderStatus
    created_at: str
    confirmed_at: Optional[str] = None
    confirmed_by: Optional[str] = None
    rejection_reason: Optional[str] = None

# ==================== USER MODELS ====================

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str
    referral_code: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(extra='ignore')
    id: str
    email: str
    username: str
    referral_code: Optional[str] = None
    referred_by: Optional[str] = None
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = 'bearer'
    user: UserResponse

# ==================== REFERRAL MODELS ====================

class ApplyReferralRequest(BaseModel):
    referral_code: str

class ApplyReferralResponse(BaseModel):
    success: bool
    message: str
    referral_code: Optional[str] = None
    referred_by: Optional[str] = None

class ReferralBonusInfo(BaseModel):
    valid_referral_count: int
    next_bonus_at: int
    next_bonus_amount: float
    total_bonus_earned: float
    bonus_history: List[Dict[str, Any]] = []

# ==================== GAME MODELS ====================

class GameAvailability(str, Enum):
    AVAILABLE = "available"
    MAINTENANCE = "maintenance"
    UNAVAILABLE = "unavailable"

class GamePlatform(str, Enum):
    ANDROID = "android"
    IOS = "ios"
    WEB = "web"

class GameCreate(BaseModel):
    name: str
    description: str
    tagline: Optional[str] = None
    thumbnail: Optional[str] = None
    icon_url: Optional[str] = None
    category: Optional[str] = None
    download_url: Optional[str] = None
    platforms: List[GamePlatform] = [GamePlatform.ANDROID]
    availability_status: GameAvailability = GameAvailability.AVAILABLE
    show_credentials: bool = True
    allow_recharge: bool = True
    is_featured: bool = False

class GameUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tagline: Optional[str] = None
    thumbnail: Optional[str] = None
    icon_url: Optional[str] = None
    category: Optional[str] = None
    download_url: Optional[str] = None
    platforms: Optional[List[GamePlatform]] = None
    availability_status: Optional[GameAvailability] = None
    show_credentials: Optional[bool] = None
    allow_recharge: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None

class GameResponse(BaseModel):
    model_config = ConfigDict(extra='ignore')
    id: str
    name: str
    description: str
    tagline: Optional[str] = None
    thumbnail: Optional[str] = None
    icon_url: Optional[str] = None
    is_active: bool
    category: Optional[str] = None
    download_url: Optional[str] = None
    platforms: List[str] = ["android"]
    availability_status: str = "available"
    show_credentials: bool = True
    allow_recharge: bool = True
    is_featured: bool = False
    display_order: int = 0
    created_by: Optional[str] = None
    created_at: datetime

class PublicGameResponse(BaseModel):
    """Public game response - safe to show without auth"""
    model_config = ConfigDict(extra='ignore')
    id: str
    name: str
    description: str
    tagline: Optional[str] = None
    thumbnail: Optional[str] = None
    icon_url: Optional[str] = None
    category: Optional[str] = None
    download_url: Optional[str] = None
    platforms: List[str] = ["android"]
    availability_status: str = "available"
    is_featured: bool = False

# ==================== CLIENT CREDENTIAL MODELS ====================

class ClientCredentialAssign(BaseModel):
    client_id: str
    game_id: str
    game_user_id: str
    game_password: str

class ClientCredentialResponse(BaseModel):
    model_config = ConfigDict(extra='ignore')
    id: str
    client_id: str
    game_id: str
    game_name: str
    game_user_id: str
    game_password: str
    is_active: bool
    assigned_at: str
    last_accessed_at: Optional[str] = None

# ==================== ADMIN MODELS ====================

class AdminDashboardStats(BaseModel):
    total_users: int
    active_users: int
    total_clients: int
    active_clients: int
    total_games: int
    pending_withdrawals: int
    pending_orders: int
    pending_loads: int
    total_withdrawals_amount: float
    total_earnings_distributed: float
    total_bonus_distributed: float
    total_ledger_in: float
    total_ledger_out: float

class AdminClientUpdate(BaseModel):
    display_name: Optional[str] = None
    status: Optional[ClientStatus] = None
    withdraw_locked: Optional[bool] = None
    load_locked: Optional[bool] = None
    bonus_locked: Optional[bool] = None
    valid_referral_count: Optional[int] = None

class AdminCredentialUpdate(BaseModel):
    game_user_id: Optional[str] = None
    game_password: Optional[str] = None
    reason: str

class AdminWalletAdjustment(BaseModel):
    amount: float
    wallet_type: WalletType
    reason: str

class AdminOrderEdit(BaseModel):
    new_amount: float
    reason: str

# ==================== GLOBAL SETTINGS MODELS ====================

class ReferralTier(BaseModel):
    """Single tier definition"""
    tier_number: int
    name: str
    min_referrals: int
    commission_percentage: float
    
class ReferralTierConfig(BaseModel):
    """Complete referral tier configuration"""
    base_percentage: float = 5.0
    tiers: List[ReferralTier] = [
        ReferralTier(tier_number=0, name="Starter", min_referrals=0, commission_percentage=5.0),
        ReferralTier(tier_number=1, name="Bronze", min_referrals=5, commission_percentage=6.0),
        ReferralTier(tier_number=2, name="Silver", min_referrals=10, commission_percentage=7.0),
        ReferralTier(tier_number=3, name="Gold", min_referrals=20, commission_percentage=8.0),
        ReferralTier(tier_number=4, name="Platinum", min_referrals=50, commission_percentage=10.0),
    ]

class BonusMilestone(BaseModel):
    """Single bonus milestone definition"""
    milestone_number: int
    referrals_required: int
    bonus_amount: float
    bonus_type: str = "bonus"  # 'bonus' or 'real'
    description: str = ""

class BonusRulesConfig(BaseModel):
    """Complete bonus rules configuration"""
    enabled: bool = True
    milestones: List[BonusMilestone] = [
        BonusMilestone(milestone_number=1, referrals_required=5, bonus_amount=5.0, description="First milestone bonus"),
        BonusMilestone(milestone_number=2, referrals_required=10, bonus_amount=2.0, description="10 referrals bonus"),
        BonusMilestone(milestone_number=3, referrals_required=15, bonus_amount=2.0, description="15 referrals bonus"),
        BonusMilestone(milestone_number=4, referrals_required=20, bonus_amount=3.0, description="20 referrals bonus"),
        BonusMilestone(milestone_number=5, referrals_required=30, bonus_amount=5.0, description="30 referrals bonus"),
        BonusMilestone(milestone_number=6, referrals_required=50, bonus_amount=10.0, description="50 referrals bonus"),
    ]
    # Legacy mode for backward compatibility
    use_legacy_mode: bool = False
    legacy_first_milestone: int = 5
    legacy_first_bonus: float = 5.0
    legacy_block_size: int = 5
    legacy_block_bonus: float = 2.0

class AntiFraudConfig(BaseModel):
    """Anti-fraud detection settings"""
    enabled: bool = True
    # IP-based detection
    max_referrals_per_ip: int = 3
    ip_cooldown_hours: int = 24
    # Time-based detection
    min_account_age_hours: int = 1
    min_deposit_for_valid_referral: float = 10.0
    # Device fingerprint (future)
    device_fingerprint_enabled: bool = False
    max_referrals_per_device: int = 2
    # Suspicious patterns
    flag_same_ip_referrals: bool = True
    flag_rapid_signups: bool = True
    rapid_signup_threshold_minutes: int = 5
    # Auto actions
    auto_flag_suspicious: bool = True
    auto_reject_fraud: bool = False

class GlobalSettings(BaseModel):
    """Complete global settings for the platform"""
    # Feature toggles
    automation_enabled: bool = True
    withdrawals_enabled: bool = True
    bonus_system_enabled: bool = True
    referral_system_enabled: bool = True
    default_visibility: VisibilityLevel = VisibilityLevel.FULL
    
    # Withdrawal settings
    min_withdrawal_amount: float = 20.0
    max_withdrawal_amount: float = 10000.0
    withdrawal_fee_percentage: float = 0.0
    
    # Referral system
    referral_tier_config: ReferralTierConfig = ReferralTierConfig()
    bonus_rules: BonusRulesConfig = BonusRulesConfig()
    anti_fraud: AntiFraudConfig = AntiFraudConfig()
    
    # Timestamps
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None

class GlobalSettingsUpdate(BaseModel):
    """Update model for global settings"""
    automation_enabled: Optional[bool] = None
    withdrawals_enabled: Optional[bool] = None
    bonus_system_enabled: Optional[bool] = None
    referral_system_enabled: Optional[bool] = None
    min_withdrawal_amount: Optional[float] = None
    max_withdrawal_amount: Optional[float] = None
    withdrawal_fee_percentage: Optional[float] = None

class ReferralTierUpdate(BaseModel):
    """Update a single tier"""
    tier_number: int
    name: Optional[str] = None
    min_referrals: Optional[int] = None
    commission_percentage: Optional[float] = None

class BonusMilestoneUpdate(BaseModel):
    """Update a single milestone"""
    milestone_number: int
    referrals_required: Optional[int] = None
    bonus_amount: Optional[float] = None
    bonus_type: Optional[str] = None
    description: Optional[str] = None

class AntiFraudUpdate(BaseModel):
    """Update anti-fraud settings"""
    enabled: Optional[bool] = None
    max_referrals_per_ip: Optional[int] = None
    ip_cooldown_hours: Optional[int] = None
    min_account_age_hours: Optional[int] = None
    min_deposit_for_valid_referral: Optional[float] = None
    flag_same_ip_referrals: Optional[bool] = None
    flag_rapid_signups: Optional[bool] = None
    rapid_signup_threshold_minutes: Optional[int] = None
    auto_flag_suspicious: Optional[bool] = None
    auto_reject_fraud: Optional[bool] = None
