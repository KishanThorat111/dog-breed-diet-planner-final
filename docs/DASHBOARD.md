**Dashboard / Status Summary**

- **Purpose:** Quick reference for what was changed, where AI integrations live, admin endpoints, and how to validate locally and in CI.

- **Backend (apps/api)**
  - **AI Vision:** `app.services.vision_service.classify_breed_with_gemini()` — sends images to Gemini Vision, robust parsing, retries, circuit breaker, model fallback to `gemini-2.5-flash-lite`.
  - **AI Enrichment:** `app.services.ai_service.enrich_diet_plan()` — calls LLM to enrich diet plans and records usage.
  - **Usage Recording:** `app.services.ai_usage_service.record_usage()` and `schedule_record()` persist AI usage and deduct credits (1 credit / 100 tokens), trial exempt.
  - **Billing & Subscriptions:** `app.models.subscription.Subscription` adds `credits_remaining` and `trial_ends_at` fields; admin top-up API added.
  - **Diet Plans:** `app.routers.diet_plans` persists generated diet plans for authenticated users; anonymous quick-generate still supported and frontend injects anonymous results into cache.
  - **Sentry:** Optional Sentry init in `app.main` using `SENTRY_DSN` and `SENTRY_RELEASE` (`sentry_release` setting). Added `.env.example` entries.

- **Frontend (apps/web)**
  - Admin pages: `/admin/ai-usage` and `/admin/credits` (basic).
  - `use-diet-plans` updated to optimistically show anonymous-generated plans.

- **Database / Migrations**
  - Added Alembic migration `0005_billing_and_ai_usage.py` to create `ai_usage` table and subscription fields.
  - Note: run `ALEMBIC_DATABASE_URL` (port 5432) when running migrations against Supabase/pgBouncer.

- **CI / Tests**
  - CI (`.github/workflows/ci.yml`) now runs `alembic upgrade head` before tests and sets `SENTRY_RELEASE` to `${{ github.sha }}`.
  - Unit tests added for billing/credits. Local test runs use SQLite; ensure `DATABASE_URL` is set appropriately for reliable runs.

- **How to validate locally**
  - Copy env examples: `cp apps/api/.env.example apps/api/.env` and `cp apps/web/.env.example apps/web/.env.local` and fill values (set `GEMINI_API_KEY` if testing real AI).
  - Start dev DB/Redis via Docker Compose (if available):

```bash
# from repo root
docker compose -f docker-compose.dev.yml up -d
cd apps/api
python -m venv .venv && . .venv/Scripts/Activate.ps1
pip install -r requirements-dev.txt
export DATABASE_URL="postgresql+asyncpg://..."  # or use sqlite for quick tests
alembic upgrade head
pytest tests/
```

- **Known runtime considerations**
  - Gemini API key required for vision flows; without it, image analysis returns a clear error instead of failing silently.
  - In-memory SQLite (`sqlite+aiosqlite:///:memory:`) uses separate connections per engine — prefer file-based sqlite for shared connection testing or run tests with the configured test DB URL.
  - Sentry is optional; set `SENTRY_DSN` and `SENTRY_RELEASE` to capture errors/releases.

- **Next recommended steps**
  - Deploy to staging, run migrations, then run the E2E scenario: register → create pet → upload image → generate diet plan (auth + anon) → verify `ai_usage` rows and credit deductions.
  - Protect admin pages with role checks in frontend routing.

If you want, I can now:
- Run CI locally (via `act`) or trigger GitHub Actions.
- Harden the admin UI (pagination, filtering) and add user-facing credit balance display.
- Add Sentry release creation step to CI.

Which of these should I do next?