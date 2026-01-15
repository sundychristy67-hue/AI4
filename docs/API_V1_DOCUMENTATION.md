# API v1 Documentation
## Referral-Based Gaming Order System

**Base URL**: `/api/v1`  
**Version**: 1.0.0

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Referral System](#referral-system)
4. [Order Management](#order-management)
5. [Webhook Notifications](#webhook-notifications)
6. [Bonus Engine](#bonus-engine)
7. [Error Codes](#error-codes)
8. [Rate Limiting](#rate-limiting)

---

## Overview

This API provides a complete system for managing gaming orders with referral bonuses. Key features include:

- **Dual Authentication**: Password-based with magic link support
- **Referral System**: Code validation with customizable perks
- **Bonus Engine**: Flexible rules per game and referral
- **Webhooks**: HMAC-signed notifications with retry logic
- **Idempotency**: Duplicate prevention for order creation

### Quick Start

```bash
# 1. Create an account
curl -X POST https://api.example.com/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "username": "player1",
    "password": "securepassword123",
    "display_name": "Player One"
  }'

# 2. Create an order
curl -X POST https://api.example.com/api/v1/orders/create \
  -H "Content-Type: application/json" \
  -d '{
    "username": "player1",
    "password": "securepassword123",
    "game_name": "dragon_quest",
    "recharge_amount": 100.00,
    "referral_code": "ABC12345"
  }'
```

---

## Authentication

### Global Auth Rule

All API endpoints **except signup** require authentication via:

1. **Username + Password** in request body
2. **Bearer Token** in Authorization header (takes precedence)

```bash
# Option 1: Username/Password
curl -X POST /api/v1/orders/validate \
  -H "Content-Type: application/json" \
  -d '{"username": "player1", "password": "pass123", ...}'

# Option 2: Bearer Token
curl -X POST /api/v1/orders/validate \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -H "Content-Type: application/json" \
  -d '{"game_name": "dragon_quest", "recharge_amount": 100}'
```

### Endpoints

#### POST /auth/signup

Create a new user account. **No authentication required.**

**Request:**
```json
{
  "username": "player1",
  "password": "securepassword123",
  "display_name": "Player One",
  "referred_by_code": "ABC12345"  // optional
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "Account created successfully",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "player1",
  "display_name": "Player One",
  "referral_code": "XYZ98765",
  "referred_by_code": "ABC12345"
}
```

**Validation Rules:**
- `username`: 3-50 chars, alphanumeric + underscores
- `password`: minimum 8 characters
- `display_name`: 1-100 characters

---

#### POST /auth/magic-link/request

Request a magic link for passwordless login.

**Request:**
```json
{
  "username": "player1",
  "password": "securepassword123"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Magic link created",
  "magic_link": "https://example.com/auth/verify?token=abc123...",
  "expires_in_seconds": 900
}
```

---

#### GET /auth/magic-link/consume

Consume a magic link token and receive an access token.

**Request:**
```
GET /api/v1/auth/magic-link/consume?token=abc123...
```

**Response (200):**
```json
{
  "success": true,
  "message": "Login successful",
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in_seconds": 604800,
  "user": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "player1",
    "display_name": "Player One",
    "referral_code": "XYZ98765"
  }
}
```

---

#### GET /auth/validate-token

Validate a Bearer token.

**Request:**
```bash
curl -X GET /api/v1/auth/validate-token \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

**Response (200):**
```json
{
  "valid": true,
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "player1",
  "expires_at": "2024-01-22T12:00:00Z"
}
```

---

## Referral System

### POST /referrals/validate

Validate a referral code and retrieve perks.

**Request:**
```json
{
  "username": "player1",
  "password": "securepassword123",
  "referral_code": "ABC12345"
}
```

**Response (200) - Valid:**
```json
{
  "success": true,
  "message": "Referral code is valid",
  "valid": true,
  "referrer_username": "referrer_user",
  "referrer_display_name": "Top Referrer",
  "perks": [
    {
      "perk_id": "perk-001",
      "percent_bonus": 10.0,
      "flat_bonus": 5.0,
      "max_bonus": 100.0,
      "min_amount": 20.0,
      "valid_until": "2024-12-31T23:59:59Z",
      "applicable_games": ["dragon_quest", "battle_arena"]
    }
  ]
}
```

**Response (200) - Invalid:**
```json
{
  "success": false,
  "message": "Invalid referral code",
  "valid": false,
  "error_code": "E2001"
}
```

**Error Cases:**
| Code | Description |
|------|-------------|
| E2001 | Invalid referral code |
| E2002 | Expired referral code |
| E2003 | Self-referral not allowed |
| E2004 | Referral already used |

---

## Order Management

### POST /orders/validate

Validate an order without creating it. Returns calculated bonuses.

**Request:**
```json
{
  "username": "player1",
  "password": "securepassword123",
  "game_name": "dragon_quest",
  "recharge_amount": 100.00,
  "referral_code": "ABC12345"
}
```

**Response (200) - Valid:**
```json
{
  "success": true,
  "message": "Order is valid",
  "valid": true,
  "game_name": "dragon_quest",
  "game_display_name": "Dragon Quest Online",
  "recharge_amount": 100.00,
  "bonus_amount": 15.00,
  "total_amount": 115.00,
  "bonus_calculation": {
    "base_amount": 100.00,
    "percent_bonus": 5.00,
    "flat_bonus": 0.00,
    "referral_bonus": 10.00,
    "total_bonus": 15.00,
    "rule_applied": "default",
    "rule_details": {
      "game_rule": {
        "percent_bonus": 5.0,
        "flat_bonus": 0,
        "max_bonus": 500.0
      },
      "referral_perk": {
        "percent_bonus": 10.0,
        "flat_bonus": 0,
        "max_bonus": 100.0
      },
      "is_first_recharge": false
    }
  }
}
```

---

### POST /orders/create

Create a new order with bonus calculation.

**Headers:**
```
Content-Type: application/json
Idempotency-Key: unique-key-12345  (optional, prevents duplicates)
```

**Request:**
```json
{
  "username": "player1",
  "password": "securepassword123",
  "game_name": "dragon_quest",
  "recharge_amount": 100.00,
  "referral_code": "ABC12345",
  "metadata": {
    "source": "mobile_app",
    "campaign": "summer_promo"
  }
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "Order created successfully",
  "order": {
    "order_id": "ord-550e8400-e29b-41d4-a716-446655440000",
    "username": "player1",
    "game_name": "dragon_quest",
    "game_display_name": "Dragon Quest Online",
    "recharge_amount": 100.00,
    "bonus_amount": 15.00,
    "total_amount": 115.00,
    "referral_code": "ABC12345",
    "referral_bonus_applied": true,
    "rule_applied": "{\"game_rule\": {...}, \"referral_perk\": {...}}",
    "status": "pending",
    "created_at": "2024-01-15T12:00:00Z",
    "metadata": {
      "source": "mobile_app",
      "campaign": "summer_promo"
    }
  }
}
```

**Order Statuses:**
| Status | Description |
|--------|-------------|
| pending | Order created, awaiting processing |
| confirmed | Order confirmed by system/admin |
| completed | Order fully processed |
| cancelled | Order cancelled |
| failed | Order failed to process |

---

### GET /orders/{order_id}

Get a specific order by ID. **Requires Bearer token.**

**Response (200):**
```json
{
  "order_id": "ord-550e8400-e29b-41d4-a716-446655440000",
  "username": "player1",
  "game_name": "dragon_quest",
  "recharge_amount": 100.00,
  "bonus_amount": 15.00,
  "total_amount": 115.00,
  "status": "confirmed",
  "created_at": "2024-01-15T12:00:00Z"
}
```

---

### POST /orders/list

Get paginated list of orders.

**Request:**
```json
{
  "username": "player1",
  "password": "securepassword123",
  "page": 1,
  "page_size": 20,
  "status": "confirmed"
}
```

**Response (200):**
```json
{
  "success": true,
  "data": [...],
  "total": 45,
  "page": 1,
  "page_size": 20,
  "has_more": true
}
```

---

### GET /orders/games/list

Get available games with bonus rules. **Public endpoint.**

**Response (200):**
```json
{
  "success": true,
  "games": [
    {
      "game_id": "game-001",
      "game_name": "dragon_quest",
      "display_name": "Dragon Quest Online",
      "description": "Epic fantasy MMORPG",
      "min_recharge_amount": 10.0,
      "max_recharge_amount": 5000.0,
      "bonus_rules": {
        "default": {
          "percent_bonus": 5.0,
          "flat_bonus": 0,
          "max_bonus": 500.0
        },
        "first_recharge": {
          "percent_bonus": 10.0,
          "flat_bonus": 5.0,
          "max_bonus": 1000.0
        }
      },
      "is_active": true
    }
  ]
}
```

---

## Webhook Notifications

### POST /webhooks/register

Register a webhook to receive event notifications.

**Request:**
```json
{
  "username": "player1",
  "password": "securepassword123",
  "webhook_url": "https://your-server.com/webhook",
  "subscribed_events": ["order.created", "order.confirmed"],
  "signing_secret": "your-secret-key-min-16-chars"
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "Webhook registered successfully",
  "webhook": {
    "webhook_id": "wh-550e8400-e29b-41d4-a716-446655440000",
    "webhook_url": "https://your-server.com/webhook",
    "subscribed_events": ["order.created", "order.confirmed"],
    "is_active": true,
    "created_at": "2024-01-15T12:00:00Z"
  }
}
```

### Webhook Payload

When an event occurs, we POST to your webhook URL:

```json
{
  "event": "order.created",
  "timestamp": "2024-01-15T12:00:00Z",
  "data": {
    "order_id": "ord-550e8400-e29b-41d4-a716-446655440000",
    "username": "player1",
    "referral_code": "ABC12345",
    "game": "dragon_quest",
    "amount": 100.00,
    "bonus_amount": 15.00,
    "total_amount": 115.00,
    "created_at": "2024-01-15T12:00:00Z"
  }
}
```

### Webhook Headers

```
Content-Type: application/json
X-Webhook-Signature: sha256=<hmac_signature>
X-Webhook-Event: order.created
X-Webhook-Delivery-ID: del-550e8400-e29b-41d4-a716-446655440000
X-Webhook-Timestamp: 2024-01-15T12:00:00Z
```

### Verifying Webhook Signatures

```python
import hmac
import hashlib

def verify_signature(payload: str, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # signature format: "sha256=<hex_digest>"
    actual = signature.replace("sha256=", "")
    return hmac.compare_digest(expected, actual)
```

```javascript
const crypto = require('crypto');

function verifySignature(payload, signature, secret) {
    const expected = crypto
        .createHmac('sha256', secret)
        .update(payload)
        .digest('hex');
    
    const actual = signature.replace('sha256=', '');
    return crypto.timingSafeEqual(
        Buffer.from(expected),
        Buffer.from(actual)
    );
}
```

### Retry Policy

- **3 retry attempts** with exponential backoff
- Delays: 5s, 10s, 20s
- Webhook disabled after 10 consecutive failures

---

## Bonus Engine

The bonus engine applies rules in this order:

1. **Game Bonus Rules**
   - `default`: Applied to all recharges
   - `first_recharge`: Applied only on first recharge per game

2. **Referral Perks**
   - Per-code custom bonuses
   - Can be game-specific
   - Usage limits and expiration

### Bonus Calculation Formula

```
game_bonus = (amount × percent_bonus%) + flat_bonus
game_bonus = min(game_bonus, max_bonus)  // Apply cap

referral_bonus = (amount × ref_percent%) + ref_flat
referral_bonus = min(referral_bonus, ref_max)  // Apply cap

total_bonus = game_bonus + referral_bonus
total_amount = amount + total_bonus
```

### Example Calculation

```
Recharge: $100 to Dragon Quest
Game Rule: 5% bonus, max $500
Referral Perk: 10% bonus, max $100

Game Bonus: $100 × 5% = $5.00 (under cap)
Referral Bonus: $100 × 10% = $10.00 (under cap)

Total Bonus: $15.00
Total Amount: $115.00
```

---

## Error Codes

| Code | Category | Description |
|------|----------|-------------|
| **Authentication (1xxx)** | | |
| E1001 | Auth | Invalid credentials |
| E1002 | Auth | User not found |
| E1003 | Auth | User already exists |
| E1004 | Auth | Invalid token |
| E1005 | Auth | Token expired |
| E1006 | Auth | Account locked |
| E1007 | Auth | Rate limited |
| **Referral (2xxx)** | | |
| E2001 | Referral | Invalid referral code |
| E2002 | Referral | Expired referral code |
| E2003 | Referral | Self-referral not allowed |
| E2004 | Referral | Referral already used |
| **Order (3xxx)** | | |
| E3001 | Order | Game not found |
| E3002 | Order | Invalid amount |
| E3003 | Order | Amount below minimum |
| E3004 | Order | Amount above maximum |
| E3005 | Order | Duplicate order |
| E3006 | Order | Order not found |
| **Webhook (4xxx)** | | |
| E4001 | Webhook | Registration failed |
| E4002 | Webhook | Webhook not found |
| E4003 | Webhook | Invalid webhook URL |
| **General (5xxx)** | | |
| E5001 | General | Validation error |
| E5002 | General | Internal error |
| E5003 | General | Database error |

---

## Rate Limiting

- **100 requests** per 60-second window per IP
- **5 failed auth attempts** triggers 15-minute lockout

**Rate Limit Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705323600
```

**Response (429):**
```json
{
  "success": false,
  "message": "Rate limit exceeded. Please try again later.",
  "error_code": "E1007"
}
```

---

## SDK Examples

### Python

```python
import requests

class GamingOrderAPI:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.auth = {"username": username, "password": password}
    
    def create_order(self, game, amount, referral_code=None):
        payload = {
            **self.auth,
            "game_name": game,
            "recharge_amount": amount,
            "referral_code": referral_code
        }
        response = requests.post(
            f"{self.base_url}/orders/create",
            json=payload
        )
        return response.json()

# Usage
api = GamingOrderAPI("https://api.example.com/api/v1", "player1", "pass123")
order = api.create_order("dragon_quest", 100.00, "ABC12345")
```

### JavaScript/Node.js

```javascript
class GamingOrderAPI {
    constructor(baseUrl, username, password) {
        this.baseUrl = baseUrl;
        this.auth = { username, password };
    }
    
    async createOrder(game, amount, referralCode = null) {
        const response = await fetch(`${this.baseUrl}/orders/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ...this.auth,
                game_name: game,
                recharge_amount: amount,
                referral_code: referralCode
            })
        });
        return response.json();
    }
}

// Usage
const api = new GamingOrderAPI('https://api.example.com/api/v1', 'player1', 'pass123');
const order = await api.createOrder('dragon_quest', 100.00, 'ABC12345');
```

---

## Changelog

### v1.0.0 (2024-01-15)
- Initial release
- Authentication with magic links
- Referral system with perks
- Order management with bonus engine
- HMAC-signed webhooks
