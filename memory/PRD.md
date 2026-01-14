# VaultLink - Unified Staffless-First Platform

## Original Problem Statement
The user wants to integrate three existing systems (`chatwoot-telegram-ai-bot`, a referral/dashboard app, and Telegram bots) into a single, production-grade, staffless-first platform. The core concept is a secure web portal for users, accessed via a "magic link" sent through a Chatwoot messenger. This portal will allow users to view their financial summary, transaction history, and referral status.

## Core Design Principles (Docker + VPS Ready)
1. **Public browsing NEVER requires login** - Games list, downloads, availability visible without auth
2. **Sensitive actions ALWAYS require login** - Game credentials, recharge, orders need authentication
3. **No silent failures** - Every action has visible state
4. **Automation must be resumable** - All state stored in database, survives restarts
5. **Stateless where possible** - Sessions revalidated on page load

## Core Requirements
- **Unified System:** A single FastAPI backend and React frontend
- **Authentication:** Magic link-based access for clients and JWT-based login for admins
- **Client Portal:** Dashboard for clients to see balances, transactions, game credentials, referral data
- **Admin Panel:** Comprehensive dashboard for managing clients, games, orders, and audit logs
- **Ledger-First Finance:** Immutable transaction log for all financial activities
- **Telegram Confirmation:** Admins confirm, reject, or edit deposit/withdrawal amounts in Telegram
- **Bonus System:** Separate, non-withdrawable bonus wallet for rewards
- **Referral System:** Multi-tiered referral program with anti-fraud measures

## Tech Stack
- **Backend:** FastAPI, MongoDB (motor driver), Pydantic, JWT
- **Frontend:** React, React Router, Tailwind CSS, Context API, Axios
- **Architecture:** Monorepo full-stack application

## Database Schema (Key Collections)
- **clients:** client_id, chatwoot_contact_id, balance, bonus_balance, referral_code, status
- **transactions/ledger_transactions:** transaction_id, client_id, type, amount, status
- **portal_sessions:** token, client_id, expires_at, is_active
- **users:** (Admins) username, email, hashed_password, is_admin
- **orders:** order_id, client_id, type, amount, status
- **games:** game_id, name, is_active
- **ai_test_logs:** id, admin_id, scenario, messages, timestamp (TEST MODE)

## Test Credentials
- **Admin:** admin@test.com / admin123
- **Client Portal:** Access via magic link from POST /api/clients/portal-session

---

## Implementation Status

### Phase 1: Bonus Wallet System - COMPLETED (Jan 2026)
- [x] Backend: Added bonus_balance to clients
- [x] Added transaction types: BONUS_EARN, BONUS_LOAD
- [x] Implemented wallet adjustments and load-to-game flow
- [x] Frontend: PortalWallets, PortalLoadGame, PortalBonusTasks pages
- [x] PortalDashboard with dual-wallet display and referral progress

### Phase 2: Admin Order Management & Telegram Confirmation - COMPLETED (Jan 2026)
- [x] Registered telegram_routes router in server.py
- [x] Backend: /api/telegram/* endpoints with internal API key auth
- [x] Admin Orders page with order listing, filters, detail modal
- [x] Edit order amount functionality (stores original amount)
- [x] Confirm/Reject order functionality
- [x] Telegram API endpoints: cash-in, cash-out, load, edit, reject, pending-orders
- **Testing:** 95.5% backend, 100% frontend pass rate

### Phase 3: Full Telegram Confirmation Logic - PENDING
- [ ] Connect Telegram bot to webhook endpoints
- [ ] Implement inline keyboard for confirm/reject/edit in Telegram
- [ ] Real-time notifications to admins

### Phase 4: Referral System Enhancements - COMPLETED (Jan 2026)
- [x] Admin-editable referral tier configuration (commission percentages)
- [x] Admin-editable bonus milestones (referral targets and rewards)
- [x] Admin-editable anti-fraud detection settings
- [x] Settings stored in MongoDB with 60-second cache
- [x] Reset to defaults functionality
- [x] Admin Settings UI with 4 tabs (General, Tiers, Milestones, Anti-Fraud)
- **Testing:** 100% backend (27/27 tests), 100% frontend pass rate

### Phase 5: Client Visibility & Password Auth - COMPLETED (Jan 2026)
- [x] Client-specific visibility levels (FULL, SUMMARY, HIDDEN)
- [x] Admin UI to set visibility per client in Client Detail page
- [x] Portal routes respect visibility - hidden clients see minimal data
- [x] Optional username/password authentication for clients
- [x] Client login page at /client-login
- [x] Portal Security Settings page for clients to set up password
- [x] Flexible auth that accepts magic link OR JWT token
- [x] Settings icon added to Portal Dashboard header
- **Testing:** Backend APIs verified via curl, Frontend UI verified via screenshots

### Phase 6: AI Test Spot & Payment Simulation Panel - COMPLETED (Jan 2026)
- [x] **AI Test Spot** - Isolated test environment for AI behavior testing
  - Route: /admin/ai-test
  - Test scenarios: Client Query, Agent Response, Payment Flow, Error Handling
  - Sample prompts for quick testing
  - Test logs stored in database
  - Clear TEST MODE indicator
- [x] **Temporary Payment Check Panel** - Internal payment verification (replaces Telegram temporarily)
  - Route: /admin/payment-panel
  - Simulate payment creation (cash-in/cash-out)
  - Mark payments as RECEIVED / FAILED
  - Adjust amounts (for mismatch testing)
  - Create test clients for testing
  - Test stats dashboard
  - Clear TEMPORARY warning indicator
- [x] Backend routes at /api/admin/test/*
- [x] Public games page as default landing (no login required)
- **Note:** Payment Panel is TEMPORARY - will be replaced by Chatwoot/Telegram integration

---

## Public vs Protected Routes

### Public (No Login Required)
- `/games` - Public games catalog
- `/api/public/games` - Games list API
- Download links on game cards
- Availability labels (Available, Maintenance, Unavailable)

### Protected (Login Required)
- `/portal/*` - Client portal (requires magic link or password auth)
- `/admin/*` - Admin dashboard (requires admin JWT)
- Game credentials viewing
- Recharge/Load functionality
- Orders & transactions

---

## MOCKED/TEMPORARY Integrations
- **Telegram Bot:** Endpoints exist at /api/telegram/* but not connected to real Telegram bot
- **Chatwoot:** Entry point for magic links (integration not started)
- **IP Tracking:** Anti-fraud IP checks require additional infrastructure to track client IPs
- **AI Test Spot:** Mock responses only - no real AI invoked
- **Payment Panel:** TEMPORARY - Will be replaced by Chatwoot/Telegram webhooks

## File Structure
```
/app/
├── backend/
│   ├── routes/
│   │   ├── admin_routes.py
│   │   ├── auth_routes.py
│   │   ├── client_routes.py
│   │   ├── portal_routes.py
│   │   ├── public_routes.py
│   │   ├── telegram_routes.py
│   │   ├── settings_routes.py
│   │   └── test_routes.py (NEW - Phase 6: AI Test & Payment Simulation)
│   ├── server.py
│   ├── models.py
│   ├── auth.py
│   ├── utils.py
│   └── config.py
├── frontend/
│   └── src/
│       ├── pages/admin/
│       │   ├── AdminDashboard.js
│       │   ├── AdminClients.js
│       │   ├── AdminClientDetail.js
│       │   ├── AdminOrders.js
│       │   ├── AdminGames.js
│       │   ├── AdminAuditLogs.js
│       │   ├── AdminSettings.js
│       │   ├── AdminAITestSpot.js (NEW - Phase 6)
│       │   └── AdminPaymentPanel.js (NEW - Phase 6)
│       └── pages/portal/
│           ├── PortalDashboard.js
│           ├── ClientLogin.js
│           └── PortalSecuritySettings.js
└── tests/
    ├── test_phase2_admin_orders.py
    └── test_phase4_settings.py
```

## Test Credentials
- **Admin:** admin@test.com / admin123
- **Client (Password Auth):** testclient / client123
- **Client Portal (Magic Link):** POST /api/clients/portal-session with chatwoot_contact_id
