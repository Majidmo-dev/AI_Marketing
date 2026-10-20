# AI Marketing SaaS — FastAPI starter

Multi-tenant starter for an agency that creates client workspaces and invites client owners. Each client has a separate subscription, brand profile, and content.

## Run locally
1. Copy `.env.example` to `.env` and set a long random `JWT_SECRET_KEY` (e.g. `openssl rand -hex 32`). Outside `ENVIRONMENT=local` the app refuses to start with a placeholder or a key under 32 characters.
2. Configure `AGENCY_ADMIN_EMAILS`, `BOOTSTRAP_ADMIN_EMAIL`, and `BOOTSTRAP_ADMIN_PASSWORD`.
3. Run `docker compose up --build`.
4. In another terminal run `docker compose exec api python -m app.bootstrap_admin`.
5. Visit http://localhost:8000/docs.

Local development creates tables automatically. In production, set `AUTO_CREATE_TABLES=false` and use Alembic migrations.

## Included
- FastAPI, PostgreSQL, async SQLAlchemy
- JWT authentication and Argon2 password hashing
- Agency-created workspaces and expiring, hashed invitation tokens
- Tenant membership checks and roles
- Stripe Checkout, customer portal, signed webhook starter
- Brand profiles and AI content generation with template fallback / optional OpenAI provider

## API routes
- `POST /api/v1/auth/login`, `GET /api/v1/auth/me`
- `POST /api/v1/clients` (agency admin creates workspace and owner invite)
- `GET /api/v1/clients`
- `POST /api/v1/invitations/accept`
- `GET/PUT /api/v1/clients/{client_id}/brand`
- `POST /api/v1/content/generate`
- `GET /api/v1/clients/{client_id}/content`
- `POST /api/v1/billing/checkout-session?client_id=...`
- `POST /api/v1/billing/portal-session?client_id=...`
- `POST /api/v1/billing/webhook`

## Before production
This is an initial scaffold, not a production-certified service. Add real transactional email delivery (the invite URL is returned only for local development), rate limits, email verification, password reset, MFA, audit logs, webhook event idempotency/replay protection, monitoring, backups, security testing, and a secret manager. Review tax, cancellations, refunds, failed-payment grace periods, and subscription terms. Social platform adapters need separate OAuth integrations and platform-specific permission/app review.
