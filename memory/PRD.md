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
│   ├── api/v1/              # API v1 Module
│   │   ├── core/            # Config, security, database
│   │   ├── models/          # Pydantic schemas
│   │   ├── routes/          # API endpoints (auth, referral, order, webhook, admin)
│   │   └── services/        # Business logic
│   ├── routes/              # Portal API routes
│   ├── services/            # Portal services
│   └── server.py            # Main FastAPI app
├── frontend/
│   └── src/pages/admin/
│       └── AdminPerksPage.js  # NEW: Admin UI for perks
├── docs/
│   └── API_V1_DOCUMENTATION.md
└── memory/
    └── PRD.md
```

## Completed Features ✅

### Jan 15, 2026 - Admin Perks UI
- **Admin Perks Page** (`/admin/perks`)
  - Dashboard stats (users, orders, volume, bonus distributed)
  - Create/Edit/Delete referral perks
  - Filter by status (active/inactive)
  - Search by referral code or game
  - View all games with bonus rules
  - User lookup for referral code selection

### API v1 Admin Endpoints (NEW)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/admin/perks` | GET | List all perks |
| `/api/v1/admin/perks` | POST | Create new perk |
| `/api/v1/admin/perks/{id}` | GET | Get specific perk |
| `/api/v1/admin/perks/{id}` | PUT | Update perk |
| `/api/v1/admin/perks/{id}` | DELETE | Delete perk |
| `/api/v1/admin/users` | GET | List users |
| `/api/v1/admin/games` | GET | List games |
| `/api/v1/admin/games/{name}/bonus-rules` | PUT | Update game bonus rules |
| `/api/v1/admin/stats` | GET | Get admin statistics |

### Previous Implementations
- PostgreSQL migration complete
- API v1 with 14+ endpoints (auth, referrals, orders, webhooks)
- Dual authentication (password + Bearer token)
- Magic link login flow
- Modular bonus engine
- HMAC-signed webhooks with retry
- Rate limiting & brute force protection
- Swagger documentation

## Test Credentials

### API v1 / Admin Perks
- **User 1:** testplayer / password123 (referral: SRJ6RENQ)
- **User 2:** player2 / password456 (referral: SK4Y7O70)

### Portal
- **Admin:** admin@test.com / admin123
- **Client:** testclient / client123

## Access Points
- **Admin Perks UI:** `/admin/perks`
- **Swagger Docs:** `/docs`
- **API v1 Base:** `/api/v1`

## Upcoming Tasks
1. Complete Telegram bot notification integration
2. Add webhook event types (order.confirmed, etc.)
3. Analytics dashboard for referral performance

## Future/Backlog
- Replace temporary payment panel
- Full Chatwoot integration
- Webhook delivery monitoring UI
- Custom perk expiration notifications
