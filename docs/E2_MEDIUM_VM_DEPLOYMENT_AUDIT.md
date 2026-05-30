# Production Deployment Audit for GCP e2-medium VM

Project: Dog Breed Diet Planner
Date: 2026-05-31
Deployment target: dog-breed-identifier (GCP asia-south1-a)

## Scope

This audit validates production readiness for:
1. Single VM
2. Docker Compose
3. Caddy TLS reverse proxy
4. Local PostgreSQL container
5. No Redis, no Kubernetes, no Cloud Run, no Supabase

## Findings and implemented changes

### 1. Infrastructure topology

Implemented:
1. Added local PostgreSQL service in [deploy/one-server/docker-compose.yml](deploy/one-server/docker-compose.yml).
2. Added persistent Docker volume postgres_data for DB durability.
3. Added Caddy and app services with dependency sequencing and health checks.

### 2. Production Docker runtime

Implemented:
1. API runtime image remains minimal Python slim and non-root.
2. Web runtime image remains standalone Next.js and non-root.
3. API startup runs Alembic migrations before serving traffic.

### 3. Environment management

Implemented:
1. API env template: [deploy/one-server/.env.api.example](deploy/one-server/.env.api.example).
2. Web env template: [deploy/one-server/.env.web.example](deploy/one-server/.env.web.example).
3. Postgres env template: [deploy/one-server/.env.postgres.example](deploy/one-server/.env.postgres.example).

### 4. Automatic HTTPS and routing

Implemented:
1. Domain routing and HTTPS in [deploy/one-server/Caddyfile](deploy/one-server/Caddyfile).
2. Redirect www to apex domain.
3. API routes proxied by path (/api, /health, /ready, docs paths).

### 5. Health and resiliency

Implemented:
1. Health checks for postgres, api, web, and proxy.
2. restart: unless-stopped on all services.
3. init and pids_limit to improve process cleanup and safety.

### 6. Logging and observability

Implemented:
1. Docker json-file rotation limits for all services.
2. API uvicorn logs configured for production-friendly info level with no access-log spam.
3. API application logging keeps production JSON formatter behavior.

### 7. GitHub Actions deployment

Implemented:
1. VM SSH deployment workflow in [.github/workflows/deploy-api.yml](.github/workflows/deploy-api.yml).
2. Removed Vercel deployment workflow to avoid conflicting targets.
3. CI workflow no longer provisions Redis.

## Memory planning (4 GB RAM)

Configured memory caps:
1. postgres: 1024 MB
2. api: 900 MB
3. web: 900 MB
4. proxy: 160 MB

Reserved by service caps total: 2984 MB.

Expected host overhead and Docker daemon:
1. Approximately 600 to 900 MB.

Expected practical steady-state:
1. Approximately 2.8 GB to 3.6 GB total system usage under normal demo traffic.

Result:
1. Fits comfortably in 4 GB RAM with headroom for moderate demo spikes.

## Security baseline

Implemented lightweight production controls:
1. HTTPS with automatic certificates (Caddy).
2. Security headers at Caddy and app layers.
3. Non-root API and web containers.
4. no-new-privileges on all services.
5. Secrets sourced from env files, not hard-coded in images.

## Final verdict

The repository is production-ready for the specified target:
1. GCP e2-medium single-VM deployment
2. Local PostgreSQL persistence
3. Automatic SSL and domain routing
4. GitHub Actions VM deploy automation

Next action:
1. Follow [docs/ONE_SERVER_VM_WORKFLOW.md](docs/ONE_SERVER_VM_WORKFLOW.md) for first-time server bootstrap and go-live sequence.
