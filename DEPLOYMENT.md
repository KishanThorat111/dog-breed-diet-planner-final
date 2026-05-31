# Dog Breed Diet Planner — Production Deployment Guide

> Status: Archived legacy guide.
>
> This document describes an older Railway/Vercel/Supabase architecture and is not the active production path for this repository.
>
> Use the current single-VM guide instead:
> - [docs/ONE_SERVER_VM_WORKFLOW.md](docs/ONE_SERVER_VM_WORKFLOW.md)
> - [deploy/one-server/docker-compose.yml](deploy/one-server/docker-compose.yml)
> - [.github/workflows/deploy-api.yml](.github/workflows/deploy-api.yml)

## Architecture Overview

```
Browser ──── Cloudflare CDN ──── Vercel (Next.js 14)
                                       │
                                       │ HTTPS
                                       ▼
                              Railway (FastAPI)
                                  │        │
                         Supabase │        │ Upstash Redis
                         (Postgres)        (Cache)
                                  │
                         Cloudflare R2
                         (Image Storage)
```

**Stack:** Vercel (web) · Railway (API) · Supabase (Postgres) · Cloudflare R2 (storage) · Upstash (Redis) · Clerk (auth) · Sentry (monitoring) · PostHog (analytics)  
**Estimated cost at launch:** ~$5-10/month (all free tiers)

---

## Prerequisites

- GitHub repository with the monorepo pushed
- Accounts at: Vercel, Railway, Supabase, Cloudflare, Upstash, Clerk, Sentry, PostHog
- `railway` CLI: `npm install -g @railway/cli`
- `vercel` CLI: `npm install -g vercel`

---

## 1. Supabase — Database Setup

### 1.1 Create Project

1. Go to [supabase.com](https://supabase.com) → New Project
2. Choose region closest to Railway deployment (e.g. `us-east-1`)
3. Note your **database password** — you'll need it once

### 1.2 Connection Strings

In Supabase Dashboard → Project Settings → Database:

| Use | URL format | Port |
|-----|-----------|------|
| **Application (via pooler)** | `postgresql+asyncpg://postgres.<ref>:<pwd>@aws-0-<region>.pooler.supabase.com:**6543**/postgres` | 6543 |
| **Alembic migrations** | `postgresql+asyncpg://postgres.<ref>:<pwd>@aws-0-<region>.pooler.supabase.com:**5432**/postgres` | 5432 |

> **Critical:** Set `DATABASE_URL` in Railway to the **port 6543** (transaction pooler) URL.  
> Set `ALEMBIC_DATABASE_URL` to the **port 5432** (session mode / direct) URL for migration commands.

### 1.3 Enable Required Extensions

In Supabase SQL Editor, run:

```sql
-- Required for UUID generation (used as default PK values)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Optional: full-text search on breed names
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

### 1.4 Run Initial Migration

After Railway deployment (section 3), run from your local machine:

```bash
# Set ALEMBIC_DATABASE_URL to the direct connection (port 5432)
export ALEMBIC_DATABASE_URL="postgresql+asyncpg://..."
cd apps/api
uv run alembic upgrade head
```

Or let Railway's `releaseCommand` in `railway.toml` handle it automatically on each deploy.

---

## 2. Upstash — Redis Setup

1. Go to [upstash.com](https://upstash.com) → Create Database
2. Region: match your Railway region
3. Enable **TLS** (required — Upstash always uses TLS)
4. Copy the **Redis URL** — it starts with `rediss://` (note double-s)

```
REDIS_URL=rediss://default:<TOKEN>@<HOST>.upstash.io:6380
```

---

## 3. Clerk — Authentication Setup

### 3.1 Create Application

1. Go to [clerk.com](https://clerk.com) → Create Application
2. Enable: Email + Google (recommended)
3. Note your **Publishable Key** and **Secret Key**

### 3.2 Get JWKS URL and Issuer

In Clerk Dashboard → API Keys → Advanced:
- **JWKS URL:** `https://<your-clerk-domain>.clerk.accounts.dev/.well-known/jwks.json`
- **Issuer:** `https://<your-clerk-domain>.clerk.accounts.dev`

### 3.3 Configure Webhook

In Clerk Dashboard → Webhooks → Add Endpoint:
- URL: `https://api.yourdomain.com/api/v1/auth/webhook`
- Events: `user.created`, `user.updated`, `user.deleted`
- Copy the **Signing Secret** (`whsec_...`)

### 3.4 Add Allowed Origins

In Clerk Dashboard → Settings → Allowed Origins:
- Add your Vercel domain: `https://your-project.vercel.app`
- Add your custom domain if applicable

---

## 4. Cloudflare R2 — Storage Setup

### 4.1 Create Bucket

1. Cloudflare Dashboard → R2 → Create Bucket
2. Name: `dog-breed-diet-planner` (or your chosen name)
3. Location hint: near your Railway region

### 4.2 Create API Token

R2 → Manage R2 API Tokens → Create API Token:
- Permissions: **Object Read & Write**
- Bucket: specific → `dog-breed-diet-planner`
- Copy **Access Key ID** and **Secret Access Key**

### 4.3 Configure CORS (for direct browser uploads if needed)

In R2 Bucket Settings → CORS:
```json
[
  {
    "AllowedOrigins": ["https://your-domain.com", "https://your-project.vercel.app"],
    "AllowedMethods": ["GET", "PUT", "POST"],
    "AllowedHeaders": ["Content-Type", "Authorization"],
    "MaxAgeSeconds": 3600
  }
]
```

### 4.4 Endpoint URL

Format: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com`

Find your Account ID in Cloudflare Dashboard → Right sidebar.

---

## 5. Railway — API Deployment

### 5.1 Initial Setup

```bash
cd apps/api
railway login
railway init          # creates new project OR links existing
railway link          # link to existing project
```

### 5.2 Set Environment Variables

```bash
# In Railway Dashboard → Your Service → Variables
# OR via CLI:
railway variables set ENVIRONMENT=production
railway variables set SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
railway variables set DATABASE_URL="postgresql+asyncpg://postgres.<ref>:<pwd>@...pooler.supabase.com:6543/postgres"
railway variables set REDIS_URL="rediss://default:<TOKEN>@<HOST>.upstash.io:6380"
railway variables set CLERK_SECRET_KEY="sk_live_..."
railway variables set CLERK_WEBHOOK_SECRET="whsec_..."
railway variables set CLERK_JWKS_URL="https://<domain>.clerk.accounts.dev/.well-known/jwks.json"
railway variables set CLERK_ISSUER="https://<domain>.clerk.accounts.dev"
railway variables set CLOUDFLARE_R2_ACCOUNT_ID="<account_id>"
railway variables set CLOUDFLARE_R2_ACCESS_KEY_ID="<key>"
railway variables set CLOUDFLARE_R2_SECRET_ACCESS_KEY="<secret>"
railway variables set CLOUDFLARE_R2_BUCKET_NAME="dog-breed-diet-planner"
railway variables set CLOUDFLARE_R2_ENDPOINT_URL="https://<account_id>.r2.cloudflarestorage.com"
railway variables set ALLOWED_ORIGINS="https://your-domain.com,https://your-project.vercel.app"
railway variables set SENTRY_DSN="https://..."
```

### 5.3 GitHub Secrets for CI/CD

In GitHub → Repository → Settings → Secrets and Variables → Actions:
```
RAILWAY_TOKEN    ← Railway Dashboard → Account Settings → Tokens
```

### 5.4 First Deploy

```bash
cd apps/api
railway up --service api
```

The `railway.toml` `releaseCommand` runs `alembic upgrade head` before traffic switches.

### 5.5 Verify Deployment

```bash
curl https://your-railway-service.up.railway.app/health
# Expected: {"status":"ok","ml_model":"loaded",...}

curl https://your-railway-service.up.railway.app/ready
# Expected: {"status":"ready","cache":"ok","ml_model":"loaded"}
```

---

## 6. Vercel — Web Deployment

### 6.1 Initial Setup

```bash
cd apps/web
vercel login
vercel link        # links to existing project or creates new
```

### 6.2 Set Environment Variables

In Vercel Dashboard → Project → Settings → Environment Variables:

| Variable | Value | Environments |
|----------|-------|-------------|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | `pk_live_...` | All |
| `CLERK_SECRET_KEY` | `sk_live_...` | All |
| `NEXT_PUBLIC_API_URL` | `https://api.yourdomain.com` | Production |
| `NEXT_PUBLIC_API_URL` | `https://your-service.up.railway.app` | Preview |
| `NEXT_PUBLIC_SENTRY_DSN` | `https://...` | All |
| `SENTRY_AUTH_TOKEN` | `sntrys_...` | All |
| `SENTRY_ORG` | `your-sentry-org` | All |
| `SENTRY_PROJECT` | `dog-breed-diet-planner-web` | All |
| `NEXT_PUBLIC_POSTHOG_KEY` | `phc_...` | Production |
| `NEXT_PUBLIC_POSTHOG_HOST` | `https://app.posthog.com` | Production |

### 6.3 GitHub Secrets for CI/CD

```
VERCEL_TOKEN       ← Vercel Dashboard → Account Settings → Tokens
VERCEL_ORG_ID      ← vercel whoami --json or Vercel team settings
VERCEL_PROJECT_ID  ← .vercel/project.json after `vercel link`
```

### 6.4 First Deploy

```bash
cd apps/web
vercel --prod
```

---

## 7. Custom Domain (Optional)

### 7.1 API Domain via Railway

In Railway → Service → Settings → Networking → Custom Domain:
- Add: `api.yourdomain.com`
- Add CNAME: `api.yourdomain.com → your-service.up.railway.app`

### 7.2 Web Domain via Vercel

In Vercel → Project → Settings → Domains:
- Add: `yourdomain.com` and `www.yourdomain.com`
- Add CNAME: `www → cname.vercel-dns.com`
- Add A record: `@` → Vercel's IP (shown in dashboard)

### 7.3 Cloudflare CDN (Optional but Recommended)

If using Cloudflare as your DNS:
1. Set Vercel domain's proxy status to **DNS only** (grey cloud) initially to get SSL
2. After Vercel SSL issues, switch to **Proxied** (orange cloud) for CDN
3. In Cloudflare → SSL/TLS → set to **Full (Strict)**
4. Create Page Rule: `api.yourdomain.com/*` → Cache Level: Bypass (API responses must not be cached)

---

## 8. GitHub Actions Secrets Summary

| Secret | Where to get it |
|--------|----------------|
| `RAILWAY_TOKEN` | Railway → Account Settings → API Tokens |
| `VERCEL_TOKEN` | Vercel → Account Settings → Tokens |
| `VERCEL_ORG_ID` | Vercel → Team Settings → General (Team ID) |
| `VERCEL_PROJECT_ID` | `.vercel/project.json` after `vercel link` |

---

## 9. ML Model Weights

The EfficientNet-B4 model weights are not in the repository (too large for Git).

**Options:**
1. **Railway Volume:** Mount at `/app/models/` and set `ML_MODEL_PATH=models/efficientnet_b4_dogs_v1.pth`
2. **Bake into Docker image:** Add `COPY models/ models/` to Dockerfile before `USER appuser`
3. **Download at startup:** Add a pre-startup script that fetches from R2

For Railway Volumes:
```bash
railway volume add --mount /app/models --size 1  # 1GB
# Then upload your model file to the volume
```

---

## 10. Monitoring Verification

After all services are live:

```bash
# Check API health
curl https://api.yourdomain.com/health | jq .

# Check API readiness (DB + Cache + Model)
curl https://api.yourdomain.com/ready | jq .

# Trigger a test error to verify Sentry is receiving events
# (check Sentry dashboard within 30s)

# Verify PostHog is receiving events
# Open your app in browser, go to PostHog → Live Events
```

---

## 11. Local Development Quick Start

```bash
# 1. Clone and install
git clone <repo>
make setup

# 2. Configure environment
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env.local
# Edit both files with your development values

# 3. Start Docker services (Postgres + Redis)
docker compose -f docker-compose.dev.yml up -d

# 4. Apply migrations
make migrate

# 5. Start everything
make dev
# API: http://localhost:8000
# Web: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

---

## 12. Production Checklist

- [ ] `SECRET_KEY` is a random 64-char hex string (not the default)
- [ ] `ENVIRONMENT=production` set in Railway
- [ ] `DATABASE_URL` uses Supabase **port 6543** (transaction pooler)
- [ ] `REDIS_URL` uses `rediss://` (TLS) Upstash URL
- [ ] All Clerk production keys (not `sk_test_`, `pk_test_`)
- [ ] `CLERK_WEBHOOK_SECRET` set and Clerk webhook configured
- [ ] `ALLOWED_ORIGINS` explicitly lists your domains (no wildcards)
- [ ] `SENTRY_DSN` configured and test error received
- [ ] Railway healthcheck passes (`/health` returns 200)
- [ ] Railway readiness check passes (`/ready` returns 200 with `"ml_model":"loaded"`)
- [ ] Alembic migrations applied (`alembic current` shows head)
- [ ] R2 CORS configured for your frontend domain
- [ ] Vercel build succeeds with no TypeScript errors
- [ ] PostHog receiving events in Live Events view
- [ ] GitHub Actions secrets set (`RAILWAY_TOKEN`, `VERCEL_TOKEN`, etc.)
