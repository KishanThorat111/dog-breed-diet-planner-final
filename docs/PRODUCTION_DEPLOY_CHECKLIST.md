Production Deploy Checklist

This checklist collects the minimal, high-impact steps to deploy the API and Web to production safely.

1) Secrets & env
- Set `SECRET_KEY` to a secure 64-hex string
- Set `ENVIRONMENT=production`
- Set `DATABASE_URL` to production DB (pooler URL if using Supabase)
- Set `SENTRY_DSN` (optional but recommended)
- Set `GEMINI_API_KEY` for Gemini Vision
- Set `ALLOWED_ORIGINS` to explicit origins only

2) Migrations
- Ensure `ALEMBIC_DATABASE_URL` points to direct DB (port 5432) for migrations
- Run: `cd apps/api && alembic upgrade head`

3) Verify health
- `curl https://api.yourdomain.com/health`
- `curl https://api.yourdomain.com/ready`

4) Post-deploy validation
- Register user, create pet, upload image, generate diet plan (authenticated flow)
- Verify `ai_usage` rows created in DB and subscription credits deducted
- Trigger a test error to ensure Sentry events appear

5) Rollback plan
- Keep DB backups and point release to a previous Docker image tag if needed

6) Notes
- If using Supabase, use port 6543 in production for the pooled connection
- Keep `GEMINI_API_KEY` scoped and rotate if exposed
