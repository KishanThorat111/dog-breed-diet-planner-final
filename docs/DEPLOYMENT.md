# Deployment Guide

## Prerequisites

- GitHub repository with secrets configured
- Clerk account (clerk.com) — free tier
- Railway account (railway.app) — $5/month hobby
- Vercel account (vercel.com) — free tier
- Cloudflare account with R2 enabled
- Upstash account (upstash.com) — free tier

---

## 1. Infrastructure Setup

### PostgreSQL (Railway)

1. Create a new Railway project
2. Add PostgreSQL service
3. Copy `DATABASE_URL` from Railway dashboard
4. Run migrations (see below)

### Redis (Upstash)

1. Create database at upstash.com
2. Select Redis, region closest to your Railway deployment
3. Copy `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`

### Cloudflare R2

1. In Cloudflare dashboard → R2 → Create bucket: `dog-breed-diet-planner`
2. Create API token with R2 read/write permissions
3. Note: Account ID, Access Key ID, Secret Access Key

### Clerk

1. Create application at clerk.com
2. Enable Google OAuth provider
3. Add webhook endpoint: `https://your-api.railway.app/api/v1/auth/webhook`
4. Enable events: `user.created`, `user.updated`, `user.deleted`
5. Copy Publishable Key, Secret Key, Webhook Secret

---

## 2. Backend Deployment (Railway)

### Environment Variables (set in Railway dashboard)

```
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=rediss://...
CLERK_SECRET_KEY=sk_live_...
CLERK_WEBHOOK_SECRET=whsec_...
CLOUDFLARE_R2_ACCOUNT_ID=...
CLOUDFLARE_R2_ACCESS_KEY_ID=...
CLOUDFLARE_R2_SECRET_ACCESS_KEY=...
CLOUDFLARE_R2_BUCKET_NAME=dog-breed-diet-planner
CLOUDFLARE_R2_ENDPOINT_URL=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
SENTRY_DSN=https://...
ENVIRONMENT=production
ALLOWED_ORIGINS=https://your-app.vercel.app
```

### Deploy

```bash
# Railway auto-deploys from GitHub main branch
# Or manually:
railway up --service api
```

### Run Migrations

```bash
railway run --service api -- alembic upgrade head
```

---

## 3. Frontend Deployment (Vercel)

### Environment Variables (set in Vercel dashboard)

```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_live_...
CLERK_SECRET_KEY=sk_live_...
NEXT_PUBLIC_API_URL=https://your-api.railway.app
NEXT_PUBLIC_SENTRY_DSN=https://...
NEXT_PUBLIC_POSTHOG_KEY=phc_...
NEXT_PUBLIC_POSTHOG_HOST=https://app.posthog.com
```

### Deploy

```bash
cd apps/web
vercel --prod
```

---

## 4. CI/CD (GitHub Actions)

The `.github/workflows/` directory contains:

- `ci.yml` — runs on every PR: lint, test, type-check
- `deploy-api.yml` — deploys backend on push to `main`
- `deploy-web.yml` — deploys frontend on push to `main`

### Required GitHub Secrets

```
RAILWAY_TOKEN
VERCEL_TOKEN
VERCEL_ORG_ID
VERCEL_PROJECT_ID
```

---

## 5. ML Model Weights

### Option A: Use Pretrained Weights (Development)

Without fine-tuned weights, the system uses ImageNet pretrained EfficientNet-B4.
This does NOT accurately classify dog breeds but validates the pipeline.

### Option B: Download Fine-Tuned Weights

```bash
# After training on Stanford Dogs Dataset:
# Place weights at: apps/api/models/efficientnet_b4_dogs_v1.pth
# Set in .env: ML_MODEL_PATH=models/efficientnet_b4_dogs_v1.pth
```

### Option C: Train from Scratch

See `apps/api/app/ml/README.md` for training instructions.

---

## 6. Staging Environment

Use Railway environments:

```bash
# Create staging environment
railway environment create staging

# Deploy to staging
railway up --environment staging --service api
```

Set `ENVIRONMENT=staging` and use separate Clerk + DB instances.

---

## 7. Monitoring

### Sentry

```bash
# Backend errors automatically reported
# Set SENTRY_DSN in environment variables
```

### PostHog

```bash
# Frontend analytics
# Set NEXT_PUBLIC_POSTHOG_KEY in environment variables
```

### Railway Metrics

Monitor CPU, memory, and request volume in Railway dashboard.
