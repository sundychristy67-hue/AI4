# Gaming Platform - Product Requirements Document

## Original Problem Statement
Build a production-intended gaming platform with:
- **Public Area (No Login):** Browse games, view availability status, download links
- **Protected Area (Login Required):** 
  - Clients: View game credentials, manage wallets, recharge/redeem, track referrals
  - Admins: Manage games, users, system settings
- **API v1:** Production-ready REST API for referral-based gaming order system

## Tech Stack
- **Frontend:** React, TailwindCSS, Shadcn/UI
- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL
- **Authentication:** JWT-based (Admin/Client) + Magic Link (API v1)
- **Integrations:** OpenAI GPT-4o via Emergent LLM Key, Telegram Bot

## Architecture
```
/app/
├── backend/
│   ├── api/v1/              # NEW: API v1 Module
│   │   ├── core/            # Config, security, database
│   │   ├── models/          # Pydantic schemas
│   │   ├── routes/          # API endpoints
│   │   └── services/        # Business logic
│   ├── routes/              # Portal API routes
│   ├── services/            # Portal services
│   ├── database.py          # PostgreSQL connection
│   ├── auth.py              # JWT authentication
│   └── server.py            # Main FastAPI app
├── frontend/
│   └── src/
├── docs/
│   └── API_V1_DOCUMENTATION.md  # API v1 docs
└── memory/
    └── PRD.md
```

## API v1 - Completed ✅ (Jan 15, 2026)

### Endpoints (Base: `/api/v1`)

#### Authentication
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/auth/signup` | POST | None | Create user account |
| `/auth/magic-link/request` | POST | Password | Request magic link |
| `/auth/magic-link/consume` | GET | Token | Get access token |
| `/auth/validate-token` | GET | Bearer | Validate token |

#### Referrals
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/referrals/validate` | POST | Password/Token | Validate referral code |

#### Orders
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/orders/validate` | POST | Password/Token | Validate order |
| `/orders/create` | POST | Password/Token | Create order |
| `/orders/{id}` | GET | Bearer | Get order |
| `/orders/list` | POST | Password/Token | List orders |
| `/orders/games/list` | GET | None | List games |

#### Webhooks
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/webhooks/register` | POST | Password/Token | Register webhook |
| `/webhooks/list` | GET | Bearer | List webhooks |
| `/webhooks/{id}` | DELETE | Bearer | Delete webhook |
| `/webhooks/{id}/deliveries` | GET | Bearer | Delivery history |

### Features Implemented
- ✅ Dual authentication (password + Bearer token)
- ✅ Magic link login flow
- ✅ Referral code validation with perks
- ✅ Modular bonus engine (per-game, per-referral rules)
- ✅ Order validation without creation
- ✅ Order creation with bonus calculation
- ✅ Idempotency keys for duplicate prevention
- ✅ HMAC-signed webhook notifications
- ✅ Webhook retry with exponential backoff
- ✅ Rate limiting (100 req/min)
- ✅ Brute force protection (5 attempts → 15 min lockout)
- ✅ Audit logging
- ✅ Swagger/OpenAPI documentation
- ✅ Markdown API guide

### Database Schema (API v1)
- `api_users` - User accounts with referral codes
- `api_magic_links` - Magic link tokens
- `api_sessions` - Session management
- `api_games` - Games with bonus rules
- `api_referral_perks` - Custom referral perks
- `api_orders` - Order records
- `api_webhooks` - Webhook registrations
- `api_webhook_deliveries` - Delivery logs
- `api_audit_logs` - Audit trail

## Portal System (Previous Implementation)

### Completed Features
- Public games page
- Admin dashboard with stats
- Client portal with wallet management
- Referral & bonus system with tiers
- AI Test Spot (GPT-4o)
- Temporary Payment Panel
- Admin configurable settings
- PostgreSQL migration

## Test Credentials

### API v1
- **User 1:** testplayer / password123 (referral: SRJ6RENQ)
- **User 2:** player2 / password456 (referral: SK4Y7O70)

### Portal
- **Admin:** admin@test.com / admin123
- **Client:** testclient / client123

## Documentation

- **Swagger UI:** `/docs`
- **ReDoc:** `/redoc`
- **API v1 Guide:** `/app/docs/API_V1_DOCUMENTATION.md`

## Upcoming Tasks
1. Complete Telegram bot notification integration
2. Production deployment configuration
3. Additional webhook events (order.confirmed, etc.)

## Future/Backlog
- Replace temporary payment panel
- Full Chatwoot integration
- Custom referral perk creation UI
- Analytics dashboard
