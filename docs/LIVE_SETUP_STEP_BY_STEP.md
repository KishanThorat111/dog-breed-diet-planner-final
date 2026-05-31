# Dog Breed Diet Planner - Complete Live Setup Guide

> Status: Archived legacy guide.
>
> This guide targets the old multi-provider flow (Railway, Vercel, Supabase) and is not the active production deployment model for this repository.
>
> For the current GCP single-VM deployment, use:
> - [docs/ONE_SERVER_VM_WORKFLOW.md](docs/ONE_SERVER_VM_WORKFLOW.md)
> - [deploy/one-server/docker-compose.yml](deploy/one-server/docker-compose.yml)
> - [.github/workflows/deploy-api.yml](.github/workflows/deploy-api.yml)

Last updated: 2026-05-30
Audience: Anyone who wants to run this project on their own accounts (GitHub, Cloudflare, Supabase, Railway, Vercel)

This guide is written for the current codebase behavior as-is.

## 1. What you will set up

You will deploy:
1. Backend API on Railway from apps/api.
2. Frontend on Vercel from apps/web.
3. PostgreSQL on Supabase.
4. Image storage on Cloudflare R2.
5. AI key from Google AI Studio (Gemini).
6. Optional auto-deploy from GitHub Actions.

## 2. Before you start

You need:
1. A GitHub repo containing this project.
2. Accounts ready: Supabase, Cloudflare, Railway, Vercel, Google AI Studio.
3. Local tools (optional but recommended): git, Node 20+, Python 3.12+, Docker.

Important current-code notes:
1. Current runtime auth is local JWT, not Clerk.
2. Auth guard is currently disabled in web app for product testing mode.
3. Core demo flow that works best: analyze image and generate quick diet plan.

## 3. Create and configure Supabase (database)

### 3.1 Create project

1. Go to Supabase dashboard.
2. Create a new project.
3. Pick a region near Railway region.
4. Save database password.

### 3.2 Get connection URI

1. Open Project Settings -> Database.
2. Copy pooled connection URI.
3. Convert prefix from postgres:// to postgresql+asyncpg://.
4. Keep port 6543 in DATABASE_URL.

Example format:
postgresql+asyncpg://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres

Why 6543 here:
1. Application traffic uses transaction pooler.
2. Alembic migration script auto-converts 6543 to 5432 internally during migration.

## 4. Create and configure Cloudflare R2 (image storage)

### 4.1 Create bucket

1. Cloudflare Dashboard -> R2 -> Create bucket.
2. Bucket name example: dog-breed-diet-planner.

### 4.2 Create R2 API token

1. R2 -> Manage R2 API tokens -> Create token.
2. Permission: Object Read and Write.
3. Scope: at least this bucket.
4. Save:
- Access Key ID
- Secret Access Key
- Account ID

### 4.3 Configure CORS on bucket

Add CORS rules for your frontend domain(s).

Recommended origins to include:
1. Your Vercel production domain.
2. Your Vercel preview domain pattern if needed.
3. Optional local origin http://localhost:3000.

If you are not sure, start simple with your production Vercel URL and add more only if required.

## 5. Create Gemini API key

1. Go to Google AI Studio.
2. Create API key.
3. Save key as GEMINI_API_KEY.

## 6. Deploy backend to Railway

### 6.1 Create Railway project and service

1. Railway -> New Project -> Deploy from GitHub repo.
2. Select this repository.
3. Set service root directory to apps/api.
4. Railway should use Dockerfile in apps/api.

### 6.2 Add Railway environment variables

Set these in Railway service Variables.

Required:
1. ENVIRONMENT = production
2. DATABASE_URL = your Supabase asyncpg URL on port 6543
3. SECRET_KEY = long random hex string
4. GEMINI_API_KEY = your Gemini key
5. CLOUDFLARE_R2_ACCOUNT_ID = from Cloudflare
6. CLOUDFLARE_R2_ACCESS_KEY_ID = from Cloudflare
7. CLOUDFLARE_R2_SECRET_ACCESS_KEY = from Cloudflare
8. CLOUDFLARE_R2_BUCKET_NAME = your bucket name
9. CLOUDFLARE_R2_ENDPOINT_URL = https://<account_id>.r2.cloudflarestorage.com
10. ALLOWED_ORIGINS = your Vercel URL

Optional but useful:
1. CLOUDFLARE_R2_PUBLIC_URL = public R2 URL if bucket is public
2. AI_ACTIVE_PROVIDER = gemini
3. AI_ENABLED = true
4. OPENAI_API_KEY = if you want fallback provider
5. ANTHROPIC_API_KEY = if you want fallback provider
6. ML_MODEL_PATH = leave empty unless you mount custom model file

Generate SECRET_KEY locally:
python -c "import secrets; print(secrets.token_hex(32))"

### 6.3 First deploy and verify

1. Trigger deploy.
2. Railway container startup command runs migrations automatically.
3. After deploy, open:
- https://<your-railway-url>/health
- https://<your-railway-url>/ready

Expected:
1. health returns status ok.
2. ready returns status ready.

If ready fails, check DATABASE_URL and Supabase network availability.

## 7. Deploy frontend to Vercel

### 7.1 Create Vercel project

1. Vercel -> New Project -> Import your GitHub repo.
2. Set Root Directory to apps/web.

### 7.2 Add Vercel environment variables

Required:
1. NEXT_PUBLIC_API_URL = https://<your-railway-url>

Optional:
1. NEXT_PUBLIC_API_DEBUG = false in production.

### 7.3 Deploy and verify

1. Deploy project.
2. Open the app URL.
3. Test Analyze page with a dog image.

## 8. Connect API and frontend correctly

After Vercel URL is final:
1. Go back to Railway variables.
2. Set ALLOWED_ORIGINS to include your Vercel URL.
3. If you use multiple domains, comma-separate all origins.

Example:
ALLOWED_ORIGINS=https://your-app.vercel.app,https://www.yourdomain.com

## 9. Custom domains (optional)

### 9.1 API domain

1. Add custom domain in Railway networking.
2. Configure DNS CNAME as Railway instructs.

### 9.2 Frontend domain

1. Add domain in Vercel project settings.
2. Configure DNS records as Vercel instructs.

### 9.3 If API uses custom domain, update frontend CSP

Current CSP connect-src in web config allows localhost and railway.app domains.
If your API host is custom (for example api.yourdomain.com), add it to connect-src in:
apps/web/next.config.ts

Then redeploy web.

## 10. GitHub Actions auto-deploy setup (optional but recommended)

If you want deployment on every push to main, add GitHub repository secrets:

Required for API deploy workflow:
1. RAILWAY_TOKEN

Required for web deploy workflow:
1. VERCEL_TOKEN
2. VERCEL_ORG_ID
3. VERCEL_PROJECT_ID

Where they are used:
1. .github/workflows/deploy-api.yml
2. .github/workflows/deploy-web.yml

How to find them:
1. Railway token: Railway account settings -> tokens.
2. Vercel token: Vercel account settings -> tokens.
3. VERCEL_ORG_ID and VERCEL_PROJECT_ID: from Vercel project linking metadata.

## 11. End-to-end smoke test checklist

Run this after both deployments:

1. API health
- GET /health returns status ok.

2. API readiness
- GET /ready returns status ready.

3. Web to API connectivity
- Open web app.
- Go to Analyze.
- Upload a dog image.
- Confirm prediction returns.

4. R2 upload check
- Prediction response contains image URL.
- Verify object appears in R2 bucket.

5. Gemini path
- Prediction works with normal image.
- If AI errors, inspect API logs for key/rate issues.

## 12. Exactly where to keep keys

### 12.1 Local development

Backend local file:
apps/api/.env

Frontend local file:
apps/web/.env.local

Templates:
1. apps/api/.env.example
2. apps/web/.env.example

### 12.2 Production

1. Railway service Variables:
- all backend secrets and API settings

2. Vercel Project Environment Variables:
- NEXT_PUBLIC_API_URL and any frontend env settings

3. GitHub repo Secrets:
- only CI/CD deploy tokens and IDs

Do not store production secrets in repository files.

## 13. Known behavior of current codebase

This guide is for current code as-is. Keep these expectations in mind:
1. Auth pages currently redirect to Analyze.
2. Auth guard is disabled for product testing mode.
3. Best-supported flow currently is analyze image and quick diet generation.
4. Some admin and report paths may need code alignment if you need those pages fully production-ready.

## 14. Troubleshooting quick map

Issue: CORS error in browser
1. Confirm Railway ALLOWED_ORIGINS includes exact Vercel URL.
2. Confirm no trailing slash mistakes.
3. If using custom API domain, update CSP connect-src in web config and redeploy.

Issue: API starts but /ready fails
1. Check DATABASE_URL format.
2. Ensure asyncpg prefix postgresql+asyncpg:// is used.
3. Ensure Supabase credentials and region host are correct.

Issue: Image upload fails
1. Verify all R2 keys and endpoint URL.
2. Verify bucket name exact match.
3. Verify R2 token permissions include read and write.
4. Verify bucket CORS includes frontend domain.

Issue: Gemini errors or no prediction
1. Verify GEMINI_API_KEY is set and valid.
2. Check provider quotas and limits in Google AI Studio.
3. Check API logs for detailed error.

Issue: CI deploy does not run
1. Confirm push is to main.
2. Confirm changed paths match workflow filters.
3. Confirm GitHub secrets are set correctly.

## 15. One-page production variable list

Railway Variables (backend):
1. ENVIRONMENT
2. DATABASE_URL
3. SECRET_KEY
4. GEMINI_API_KEY
5. AI_ACTIVE_PROVIDER
6. AI_ENABLED
7. CLOUDFLARE_R2_ACCOUNT_ID
8. CLOUDFLARE_R2_ACCESS_KEY_ID
9. CLOUDFLARE_R2_SECRET_ACCESS_KEY
10. CLOUDFLARE_R2_BUCKET_NAME
11. CLOUDFLARE_R2_ENDPOINT_URL
12. CLOUDFLARE_R2_PUBLIC_URL
13. ALLOWED_ORIGINS
14. OPENAI_API_KEY (optional)
15. ANTHROPIC_API_KEY (optional)
16. ML_MODEL_PATH (optional)

Vercel Variables (frontend):
1. NEXT_PUBLIC_API_URL
2. NEXT_PUBLIC_API_DEBUG (optional)

GitHub Secrets (for auto-deploy):
1. RAILWAY_TOKEN
2. VERCEL_TOKEN
3. VERCEL_ORG_ID
4. VERCEL_PROJECT_ID

Done. If these steps are followed, the project should deploy and run on your own cloud accounts with the current codebase behavior.
