# Gaming Platform - Product Requirements Document

## Original Problem Statement
Build a production-intended gaming platform with:
- **Public Area (No Login):** Browse games, view availability status, download links
- **Protected Area (Login Required):** 
  - Clients: View game credentials, manage wallets, recharge/redeem, track referrals
  - Admins: Manage games, users, system settings

## Tech Stack
- **Frontend:** React, TailwindCSS, Shadcn/UI
- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL (migrated from MongoDB on Jan 15, 2026)
- **Authentication:** JWT-based dual systems (Admin + Client)
- **Integrations:** OpenAI GPT-4o via Emergent LLM Key, Telegram Bot (in progress)

## Architecture
```
/app/
├── backend/
│   ├── routes/           # API route modules
│   ├── services/         # Business logic (telegram_service.py)
│   ├── database.py       # PostgreSQL connection (asyncpg)
│   ├── auth.py           # JWT authentication
│   ├── config.py         # Settings
│   ├── models.py         # Pydantic models
│   └── server.py         # FastAPI app
├── frontend/
│   ├── src/
│   │   ├── components/   # Reusable components
│   │   ├── contexts/     # AuthContext
│   │   └── pages/        # admin/, portal/, public
│   └── App.js
└── memory/
    └── PRD.md
```

## Database Schema (PostgreSQL)
- **users:** Admin accounts (id, email, username, password_hash, role)
- **clients:** Player accounts (client_id, display_name, username, referral_code, wallet info)
- **games:** Game catalog (id, name, description, download_url, availability_status)
- **orders:** Transactions (order_id, client_id, amount, status, type)
- **ledger_transactions:** Financial ledger (IN, OUT, ADJUST, REFERRAL_EARN, BONUS)
- **client_credentials:** Game credentials per client
- **client_referrals:** Referral tracking
- **global_settings:** Platform configuration
- **audit_logs:** Admin action logs
- **ai_test_logs:** AI Test Spot logs

## Completed Features ✅

### Jan 15, 2026
- **PostgreSQL Migration:** Complete migration from MongoDB to PostgreSQL
  - All route files updated for asyncpg
  - Database schema with tables and indexes
  - Admin and client authentication working
  - Test data seeded

### Previous Session
- Public games page with search/filter
- Admin dashboard with stats
- Client portal with wallet management
- Referral & bonus system with tiers
- AI Test Spot connected to GPT-4o
- Temporary Payment Panel for simulation
- Admin settings for referral criteria, greeting messages
- Telegram bot service files created

## In Progress 🔄
- **Telegram Bot Integration:** 
  - Service file exists (`telegram_service.py`)
  - Admin routes created (`telegram_admin_routes.py`)
  - Needs: User's chat_id, full integration testing

## Credentials
- **Admin:** admin@test.com / admin123
- **Client:** testclient / client123

## API Endpoints
- `POST /api/auth/login` - Admin login
- `POST /api/portal/auth/login` - Client login
- `GET /api/public/games` - Public game list
- `GET /api/admin/dashboard-stats` - Admin stats
- `GET /api/portal/dashboard` - Client dashboard
- `POST /api/admin/test/ai-test/simulate` - AI Test Spot

## Upcoming Tasks
1. Complete Telegram notification integration
2. Full testing of all flows
3. Production hardening

## Future/Backlog
- Replace temporary payment panel with production solution
- Full Chatwoot integration
- Enhanced AI prompts
- Refactor large components (AdminSettings.js)
