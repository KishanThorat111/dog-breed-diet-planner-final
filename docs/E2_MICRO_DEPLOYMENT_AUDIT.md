# e2-micro Deployment Readiness Audit and Optimization Report

Project: Dog Breed Diet Planner
Date: 2026-05-30
Target: Google Cloud Compute Engine e2-micro (about 1 GB RAM)
Goal: portfolio-grade demo deployment with near-zero monthly infra cost

## Executive Verdict

Deployment is now viable on a free-tier e2-micro VM for light demo usage.

The repository previously had local-ML runtime complexity (PyTorch and model predownload) that was not suitable for 1 GB RAM. The deployment profile has been refactored to Gemini-only inference and a smaller container footprint.

Expected steady-state memory is below 700 MB with current resource caps.

## Phase 1 - Repository Audit Findings

### Unnecessary complexity found

1. Local ML runtime in backend deployment path:
   1. PyTorch, torchvision, timm in runtime requirements
   2. EfficientNet weights predownload during Docker build
   3. Local inference fallback path in prediction service
2. Multi-provider AI configuration (Gemini, OpenAI, Anthropic) for a demo target
3. Dev/test dependencies included in runtime requirements file
4. API Dockerfile had extra layers and heavyweight initialization steps
5. Admin router had duplicate endpoint declarations for users and stats
6. Deployment docs mixed multiple platforms and higher-complexity stack assumptions

### Not appropriate for 1 GB VM

1. Local model downloads and local model inference runtime
2. Multiple optional provider SDKs when only one provider is needed
3. Broad, stale deployment docs that include unnecessary services

### Already acceptable

1. No required local Redis in runtime path
2. No Elasticsearch, no Ollama, no local LLM server
3. Database is external (Supabase)
4. Reverse proxy model is simple (Caddy)

## Phase 2 - e2-micro Optimization Changes

### Runtime strategy

1. Gemini API only for AI operations
2. Removed local ML fallback from prediction flow
3. Kept single Uvicorn worker
4. Kept DB external in Supabase
5. Kept cache in-process only

### Configuration simplification

1. Removed local model env expectations from active templates
2. Removed fallback provider settings from active deployment templates
3. Added conservative rate-limit defaults in deployment env template

## Phase 3 - Docker Optimization Changes

### API container

1. Removed local ML wheels and model predownload path
2. Removed extra provider SDK dependencies from runtime install path
3. Removed unnecessary curl dependency in image
4. Simplified image layers and retained non-root runtime
5. Kept healthcheck with lightweight Python URL call

### Web container

1. Kept standalone Next.js runtime pattern
2. Added low-memory Node options for build and runtime
3. Kept non-root runtime user

### Build context optimization

1. Added apps/api/.dockerignore
2. Added apps/web/.dockerignore

## Phase 4 - One-Server Architecture Validation

Validated and improved:

1. deploy/one-server/docker-compose.yml
2. deploy/one-server/Caddyfile
3. deploy/one-server/.env.api.example
4. deploy/one-server/.env.web.example
5. docs/ONE_SERVER_VM_WORKFLOW.md

### Behavior targets

1. Frontend at https://app.domain.com
2. Backend at https://app.domain.com/api
3. Health at https://app.domain.com/health
4. Ready at https://app.domain.com/ready
5. Single-domain routing removes normal CORS mismatch cases

### Compose optimizations

1. Added memory caps per container
2. Added CPU caps per container
3. Added pid limits
4. Added init and no-new-privileges
5. Added bounded log file rotation

### Caddy optimizations

1. Explicit API path matcher and handlers
2. Security headers at proxy level
3. Caddy admin endpoint disabled

## Phase 5 - Memory Budget Estimate

Expected steady-state memory on e2-micro (approximate):

1. Caddy: 35 MB to 55 MB
2. FastAPI container: 150 MB to 230 MB
3. Next.js standalone container: 180 MB to 260 MB
4. Docker engine and overhead: 90 MB to 130 MB

Estimated total steady-state:

1. Lower typical: 455 MB
2. Upper typical: 675 MB

Target check:

1. Under 700 MB steady-state target: yes, expected

If memory pressure appears:

1. Disable R2 upload path by leaving R2 vars blank
2. Keep API and web log verbosity minimal
3. Keep only one browser tab and low request volume during demo
4. Add 2 GB swap to prevent OOM during image builds

## Phase 6 - Lightweight Security for Demo

Implemented and retained:

1. HTTPS via Caddy
2. Security headers in backend and proxy
3. Environment-based secret handling
4. Non-root containers where practical
5. no-new-privileges in compose services

Not added intentionally:

1. Kubernetes
2. service mesh
3. distributed tracing stack
4. heavy monitoring stack

## Phase 7 - Deployment Readiness Checklist

1. Create Google Cloud e2-micro VM
2. Open ports 22, 80, 443
3. Install Docker
4. Install Docker Compose
5. Clone repository
6. Configure env files
7. Configure domain
8. Start stack
9. Verify deployment

Detailed runbook:

1. docs/ONE_SERVER_VM_WORKFLOW.md

## Phase 8 - Final Output Summary

### Key code and config changes made

1. Removed local ML fallback from analyze runtime
2. Simplified AI runtime to Gemini-only in active factory/config path
3. Reduced API runtime dependencies
4. Simplified API Dockerfile for low-memory deployment
5. Tuned web Dockerfile memory settings
6. Added dockerignore files for smaller build context
7. Tuned one-server compose resource limits and logging
8. Hardened Caddy routing and headers
9. Updated env templates for Gemini-only and optional R2
10. Updated one-server workflow to GCP e2-micro guidance
11. Fixed duplicate admin route declarations
12. Updated prediction tests to Gemini mock path

### Cost impact analysis

With this architecture:

1. VM: free tier target on e2-micro
2. Database: Supabase free tier (within limits)
3. AI: Gemini free tier (within limits)
4. Storage: R2 optional, can be kept minimal

Expected monthly infra cost for light demo usage:

1. Target: about 0 INR
2. Risk of non-zero cost: mostly from over-usage of external service quotas

### Final deployment verdict

Approved for portfolio/demo deployment on free-tier e2-micro, provided usage stays light and external free-tier limits are respected.
