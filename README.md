# Security Monitoring Platform (MVP Foundation)

Initial implementation includes:
- Multi-tenant FastAPI backend with JWT auth and role model (owner/admin/analyst/viewer)
- Access + refresh token flow with logout token revocation in Redis
- PostgreSQL via SQLModel with persisted websites, scan runs, findings, alerts, subscriptions
- Celery + Redis task queue for asynchronous security scans
- Real scan checks: uptime, SSL expiry, security headers, common exposed ports
- Stripe webhook endpoint for subscription lifecycle events
- Stripe Checkout session endpoint for hosted subscription flow
- OAuth connect flow for Google/Facebook (when credentials are configured)
- Built-in test UI page for register/login/site/scan flow
- Docker Compose stack for local development

## Run locally

1. Start stack:
   ```bash
   docker compose up --build
   ```
2. API docs:
   - Swagger UI: http://localhost:8000/docs
   - Test UI: http://localhost:8000/
3. Health check:
   - GET http://localhost:8000/api/v1/health

## Database migrations (Alembic)

Migrations are now the source of truth for schema changes.

1. Apply migrations:
   ```bash
   docker compose exec api alembic upgrade head
   ```
2. Create a new migration after model changes:
   ```bash
   docker compose exec api alembic revision --autogenerate -m "describe_change"
   ```
3. Rollback one revision:
   ```bash
   docker compose exec api alembic downgrade -1
   ```

Note: API startup already runs `alembic upgrade head` automatically in Docker Compose.

## API quick flow

1. Register user:
   - POST `/api/v1/auth/register`
2. Login:
   - POST `/api/v1/auth/login` (OAuth2 form, username=email)
3. Refresh token:
   - POST `/api/v1/auth/refresh`
4. Logout (revoke refresh token):
   - POST `/api/v1/auth/logout`
5. Authenticated profile:
   - GET `/api/v1/users/me`
6. Create website:
   - POST `/api/v1/websites`
7. Enqueue a scan:
   - POST `/api/v1/scans/enqueue`
8. Read results:
   - GET `/api/v1/scans/runs`
   - GET `/api/v1/findings`
   - GET `/api/v1/alerts`

## OAuth setup (Google/Facebook)

Set values in backend/.env:
- GOOGLE_CLIENT_ID
- GOOGLE_CLIENT_SECRET
- GOOGLE_REDIRECT_URI (default: http://localhost:8000/api/v1/oauth/google/callback)
- FACEBOOK_CLIENT_ID
- FACEBOOK_CLIENT_SECRET
- FACEBOOK_REDIRECT_URI (default: http://localhost:8000/api/v1/oauth/facebook/callback)

Start OAuth from:
- GET `/api/v1/oauth/google/start`
- GET `/api/v1/oauth/facebook/start`

## Stripe webhook setup

Set values in backend/.env:
- STRIPE_API_KEY
- STRIPE_WEBHOOK_SECRET
- STRIPE_PRICE_BASIC_ID
- STRIPE_PRICE_PRO_ID

Webhook endpoint:
- POST `/api/v1/billing/stripe/webhook`

Checkout endpoint:
- POST `/api/v1/billing/stripe/checkout-session`

Billing portal endpoint:
- POST `/api/v1/billing/stripe/portal`

Local Stripe workflow (no local Stripe CLI install required):
1. Start listener through Docker:
   ```powershell
   .\scripts\stripe-listen.ps1
   ```
2. Copy shown webhook secret into `backend/.env` as `STRIPE_WEBHOOK_SECRET` and restart API:
   ```bash
   docker compose up -d
   ```
3. Trigger test events:
   ```powershell
   .\scripts\stripe-trigger.ps1 -Event checkout.session.completed
   .\scripts\stripe-trigger.ps1 -Event customer.subscription.updated
   ```

When testing locally, configure Stripe CLI to forward events to:
- http://localhost:8000/api/v1/billing/stripe/webhook

## AI Assistant (Groq)

The platform includes an AI assistant powered by Groq for security insights and verification.

### Setup
1. Get a free API key from [console.groq.com](https://console.groq.com/keys)
2. Add to `backend/.env`:
   ```
   GROQ_API_KEY=gsk_your_key_here
   ```
3. Rebuild and restart:
   ```bash
   docker compose up --build
   ```

### Features
- **Security Tips**: Get personalized, prioritized security recommendations based on your monitored websites and findings
- **Posture Verification**: AI-powered security posture assessment with confidence scores
- **Finding Analysis**: Click "AI Analyze" on any finding for expert explanation, severity assessment, and remediation advice

### Trust & Transparency
- The AI status is always visible (Online/Offline) in the assistant panel
- All AI responses include confidence levels (high/medium/low)
- The assistant clearly states when it's unavailable and why
- No AI feature is hidden — users always know when they're interacting with AI vs. automated scan data

## Notes
- Local Postgres host port is 5433 (container still uses 5432).
- SMTP fields are optional; without SMTP config, email alerts are recorded as failed in alerts table.
- OAuth requires provider credentials to complete the external login handshake.
- Auth security controls are Redis-backed: rate limit + temporary lockout after repeated failed logins.
- Stripe webhooks are idempotent (event tracking persisted in DB).

## Test suite

Run smoke tests in container:
```bash
docker compose exec api pytest -q
```
