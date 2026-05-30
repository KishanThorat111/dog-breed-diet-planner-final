# Single-VM Production Deployment Workflow (GCP)

Last updated: 2026-05-31

Target environment:
1. VM name: dog-breed-identifier
2. Cloud: Google Cloud Platform
3. Region: asia-south1
4. Zone: asia-south1-a
5. Machine type: e2-medium
6. CPU and RAM: 2 vCPU, 4 GB
7. Disk: 50 GB balanced persistent disk
8. Static IP: 8.231.121.51
9. Domain: dogbreeddetector.online

Architecture:
1. One Ubuntu VM running Docker Compose
2. Caddy reverse proxy with automatic HTTPS
3. FastAPI API container
4. Next.js web container
5. PostgreSQL container with persistent volume
6. No Redis
7. No Kubernetes
8. No Cloud Run
9. No Supabase

Routing:
1. Frontend: https://dogbreeddetector.online
2. Backend: https://dogbreeddetector.online/api
3. Health: https://dogbreeddetector.online/health
4. Readiness: https://dogbreeddetector.online/ready

## 1. Files used for deployment

1. [deploy/one-server/docker-compose.yml](deploy/one-server/docker-compose.yml)
2. [deploy/one-server/Caddyfile](deploy/one-server/Caddyfile)
3. [deploy/one-server/.env.api.example](deploy/one-server/.env.api.example)
4. [deploy/one-server/.env.web.example](deploy/one-server/.env.web.example)
5. [deploy/one-server/.env.postgres.example](deploy/one-server/.env.postgres.example)

## 2. DNS configuration

Use Hostinger DNS or Cloudflare DNS:
1. A record: @ -> 8.231.121.51
2. A record: www -> 8.231.121.51

If using Cloudflare proxy:
1. Start with proxy OFF for initial certificate issuance.
2. Enable proxy after HTTPS is confirmed.

## 3. VM setup commands

Run on Ubuntu 24.04 VM:
1. sudo apt update
2. sudo apt install -y ca-certificates curl git
3. curl -fsSL https://get.docker.com | sh
4. sudo usermod -aG docker $USER
5. newgrp docker
6. docker compose version

Optional for smoother build performance:
1. sudo fallocate -l 4G /swapfile
2. sudo chmod 600 /swapfile
3. sudo mkswap /swapfile
4. sudo swapon /swapfile

## 4. Clone and prepare env files

1. sudo mkdir -p /opt
2. sudo chown $USER:$USER /opt
3. git clone <repo-url> /opt/dog-breed-identifier
4. cd /opt/dog-breed-identifier/deploy/one-server
5. cp .env.api.example .env.api
6. cp .env.web.example .env.web
7. cp .env.postgres.example .env.postgres

Edit .env.postgres:
1. POSTGRES_USER
2. POSTGRES_PASSWORD
3. POSTGRES_DB

Edit .env.api:
1. SECRET_KEY
2. GEMINI_API_KEY
3. DATABASE_URL must match .env.postgres credentials
4. ALLOWED_ORIGINS=https://dogbreeddetector.online,https://www.dogbreeddetector.online

Edit .env.web:
1. NEXT_PUBLIC_API_URL=https://dogbreeddetector.online
2. NEXT_PUBLIC_API_DEBUG=false

## 5. Start stack

From /opt/dog-breed-identifier/deploy/one-server:
1. docker compose up -d --build

## 6. Verify deployment

1. curl -I https://dogbreeddetector.online
2. curl https://dogbreeddetector.online/health
3. curl https://dogbreeddetector.online/ready
4. Open web UI and run analyze flow

## 7. Operations

1. docker compose ps
2. docker compose logs -f proxy
3. docker compose logs -f api
4. docker compose logs -f web
5. docker compose logs -f postgres
6. docker compose up -d --build
7. docker compose restart api

## 8. GitHub Actions auto-deploy

Workflow file:
1. [.github/workflows/deploy-api.yml](.github/workflows/deploy-api.yml)

Required GitHub secrets:
1. GCP_VM_SSH_USER
2. GCP_VM_SSH_PRIVATE_KEY

Deployment behavior:
1. SSH into 8.231.121.51
2. Pull latest main branch in /opt/dog-breed-identifier
3. Validate env files exist
4. Run docker compose up -d --build --remove-orphans

## 9. Troubleshooting

Issue: Caddy returns 502
1. docker compose ps
2. docker compose logs -f api
3. docker compose logs -f web

Issue: /ready returns not ready
1. Check postgres container health
2. Verify DATABASE_URL user/password/db match .env.postgres

Issue: SSL certificate not issued
1. DNS not propagated
2. Port 80 blocked in VPC firewall
3. Cloudflare proxy enabled before first issuance

## 10. Restart-safe persistence

PostgreSQL data path:
1. Docker volume postgres_data mapped to /var/lib/postgresql/data

Caddy certificate storage:
1. Docker volume caddy_data
2. Docker volume caddy_config

## 11. Final production checklist

1. VM provisioned with exact target spec
2. Ports 22, 80, 443 open
3. DNS points to 8.231.121.51
4. env files created and secrets set
5. docker compose up -d --build successful
6. /health and /ready passing
7. GitHub deploy secrets configured
