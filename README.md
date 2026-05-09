# ?? Dog Breed Diet Planner

An AI-powered SaaS that identifies your dog's breed from a photo and generates a personalized diet plan based on NRC/AAFCO nutritional guidelines.

**Tech Stack**: FastAPI · Next.js 14 · PostgreSQL (Supabase) · Cloudflare R2 · Gemini API · Railway · Vercel

---

## Required Services (Free Tiers Work)

| Service | Purpose | Free Tier |
|---------|---------|-----------|
| [Supabase](https://supabase.com) | PostgreSQL database | ? 500 MB |
| [Cloudflare R2](https://dash.cloudflare.com) | Image storage | ? 10 GB |
| [Google AI Studio](https://aistudio.google.com) | Gemini API key | ? Free |
| [Railway](https://railway.app) | Backend hosting | ? $5 credit |
| [Vercel](https://vercel.com) | Frontend hosting | ? Free |

---

## Local Development Setup

### Prerequisites

- Python 3.12+  ?  https://www.python.org/downloads/
- Node.js 18+   ?  https://nodejs.org/
- PostgreSQL 15+ ? https://www.postgresql.org/download/ **or** use Supabase cloud

### 1. Clone the repo

```bash
git clone https://github.com/your-username/dog-breed-diet-planner.git
cd dog-breed-diet-planner
```

### 2. Backend setup

```bash
cd apps/api

# Create virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Copy environment file and fill in your values
cp .env.example .env
```

Edit `apps/api/.env`:

```env
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@localhost:5432/dogdiet
SECRET_KEY=<run: python -c "import secrets; print(secrets.token_hex(32))">
GEMINI_API_KEY=your-gemini-key-from-aistudio.google.com
AI_ENABLED=true

# Cloudflare R2
CLOUDFLARE_R2_ACCOUNT_ID=your-account-id
CLOUDFLARE_R2_ACCESS_KEY_ID=your-access-key-id
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your-secret-access-key
CLOUDFLARE_R2_BUCKET_NAME=dog-diet-uploads
CLOUDFLARE_R2_PUBLIC_URL=https://your-bucket.your-account.r2.cloudflarestorage.com

ALLOWED_ORIGINS=http://localhost:3000
```

```bash
# Create the local database
createdb dogdiet

# Run migrations
alembic upgrade head

# Start the backend
uvicorn app.main:app --reload --port 8000
```

Backend ? http://localhost:8000  
API docs ? http://localhost:8000/docs

### 3. Frontend setup

```bash
cd apps/web

npm install

cp .env.example .env.local
# Edit .env.local ? NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev
```

Frontend ? http://localhost:3000

### 4. Create your first admin account

1. Register at http://localhost:3000/sign-up
2. Promote yourself to admin:

```bash
cd apps/api
python -c "
import asyncio
from app.database import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import update

async def make_admin(email):
    async with AsyncSessionLocal() as db:
        await db.execute(update(User).where(User.email == email).values(is_admin=True))
        await db.commit()
        print(f'Done: {email} is now admin')

asyncio.run(make_admin('your@email.com'))
"
```

---

## Deploying to Production

### Step 1 — Set up Supabase (database)

1. Create a project at https://supabase.com
2. Go to **Settings ? Database ? Connection string ? URI**
3. Copy the URI and change `postgres://` ? `postgresql+asyncpg://`, use **port 6543**

Example:
```
postgresql+asyncpg://postgres.xxxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

### Step 2 — Set up Cloudflare R2 (image storage)

1. Go to https://dash.cloudflare.com ? **R2** ? Create bucket
2. Go to **R2 ? Manage API Tokens** ? Create token with Read+Write access
3. Note your Account ID, Access Key, and Secret Key

### Step 3 — Deploy backend to Railway

1. Go to https://railway.app ? **New Project** ? **Deploy from GitHub**
2. Select your repo. Railway detects `apps/api/Dockerfile` automatically.
3. Set **Root Directory** to `apps/api` in Railway settings.
4. Add these environment variables in Railway:

```
ENVIRONMENT=production
DATABASE_URL=<your supabase connection string from Step 1>
SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
GEMINI_API_KEY=<your key>
AI_ENABLED=true
CLOUDFLARE_R2_ACCOUNT_ID=<from Step 2>
CLOUDFLARE_R2_ACCESS_KEY_ID=<from Step 2>
CLOUDFLARE_R2_SECRET_ACCESS_KEY=<from Step 2>
CLOUDFLARE_R2_BUCKET_NAME=dog-diet-uploads
CLOUDFLARE_R2_PUBLIC_URL=<your R2 public bucket URL>
ALLOWED_ORIGINS=https://your-app.vercel.app
```

5. Run migrations after first deploy:

```bash
npm install -g @railway/cli
railway login
railway run alembic upgrade head
```

### Step 4 — Deploy frontend to Vercel

1. Go to https://vercel.com ? **New Project** ? Import from GitHub
2. Set **Root Directory** to `apps/web`
3. Add environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend.railway.app
   ```
4. Deploy. Update `ALLOWED_ORIGINS` in Railway with your Vercel URL.

---

## Environment Variables Reference

### Backend (`apps/api/.env`)

| Variable | Description | Required |
|----------|-------------|----------|
| `ENVIRONMENT` | `development` or `production` | ? |
| `DATABASE_URL` | PostgreSQL asyncpg connection string | ? |
| `SECRET_KEY` | Random 32-byte hex string for JWT | ? |
| `GEMINI_API_KEY` | Google AI Studio API key | For AI features |
| `AI_ENABLED` | `true` / `false` | ? |
| `CLOUDFLARE_R2_ACCOUNT_ID` | Cloudflare account ID | ? |
| `CLOUDFLARE_R2_ACCESS_KEY_ID` | R2 token key | ? |
| `CLOUDFLARE_R2_SECRET_ACCESS_KEY` | R2 token secret | ? |
| `CLOUDFLARE_R2_BUCKET_NAME` | Bucket name | ? |
| `CLOUDFLARE_R2_PUBLIC_URL` | Public URL for uploads | ? |
| `ALLOWED_ORIGINS` | Comma-separated frontend URLs | ? |
| `OPENAI_API_KEY` | Optional fallback AI | ? |
| `ANTHROPIC_API_KEY` | Optional fallback AI | ? |

### Frontend (`apps/web/.env.local`)

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | ? |

---

## Troubleshooting

**"Connection refused" on backend startup**  
? PostgreSQL is not running. Check `DATABASE_URL` in `.env`.

**"Invalid token" on API calls**  
? `SECRET_KEY` changed. Sign out and sign back in.

**R2 upload errors**  
? Add your frontend domain to CORS in the Cloudflare R2 dashboard.

**503 "AI model not available"**  
? Model is still loading. Wait a few seconds and retry.

**Dashboard shows blank / redirects to sign-in**  
? You are not logged in. Visit `/sign-up` to register.

---

## Project Structure

```
dog-breed-diet-planner/
+-- apps/
¦   +-- api/                  # FastAPI backend
¦   ¦   +-- app/
¦   ¦   ¦   +-- ai/           # AI provider layer (Gemini, OpenAI, Anthropic)
¦   ¦   ¦   +-- middleware/   # JWT auth (HS256, no external service)
¦   ¦   ¦   +-- ml/           # EfficientNet-B4 breed classifier
¦   ¦   ¦   +-- models/       # SQLAlchemy ORM models
¦   ¦   ¦   +-- routers/      # REST API endpoints
¦   ¦   ¦   +-- services/     # Business logic
¦   ¦   ¦   +-- utils/        # In-memory cache, R2 storage
¦   ¦   +-- migrations/       # Alembic database migrations
¦   ¦   +-- pyproject.toml
¦   +-- web/                  # Next.js 14 frontend
¦       +-- src/
¦       ¦   +-- app/          # App Router pages
¦       ¦   +-- components/   # UI components
¦       ¦   +-- hooks/        # TanStack Query data hooks
¦       ¦   +-- lib/          # API client, JWT storage
¦       +-- package.json
+-- README.md
```

## Estimated Monthly Cost (Production)

| Service | Free Tier | If exceeded |
|---------|-----------|-------------|
| Supabase | $0 (500 MB DB) | $25/mo |
| Cloudflare R2 | $0 (10 GB storage) | $0.015/GB |
| Railway | $0 ($5 credit) | ~$5-10/mo |
| Vercel | $0 (hobby plan) | $20/mo |
| Google Gemini | $0 (generous free tier) | Pay-per-use |
| **Total** | **$0/mo** | **~$30-55/mo** |
