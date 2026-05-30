# Dog Breed Diet Planner - Confluence Master Documentation

Document status: Draft
Last updated: 2026-05-27
Prepared by: Engineering
Audience: Product, Engineering, QA, DevOps, Support, Leadership

---

## 1. How to Use This Document in Confluence

This file is intentionally written as a Confluence-ready master page.

Recommended Confluence setup:
1. Create a parent page named Dog Breed Diet Planner - Engineering Documentation.
2. Copy this file content into the parent page initially.
3. Optionally split each major section into child pages over time.
4. Keep Section 22 (Known Gaps and Remediation) actively maintained as a source of truth.

Suggested Confluence page tree:
1. Home and Product Overview
2. Architecture and System Context
3. Tech Stack and Dependencies
4. Backend Services and API Reference
5. Frontend Architecture and UX Flows
6. Data Model and Migrations
7. AI, ML, and Diet Engine
8. Security and Compliance
9. Dev Setup and Local Runbooks
10. Deployment and Operations
11. Testing, CI/CD, and Quality Gates
12. Known Gaps and Remediation Plan
13. Roadmap and Future Enhancements

---

## 2. Executive Summary

Dog Breed Diet Planner is an AI-powered SaaS platform that:
1. Accepts a dog image upload or camera capture.
2. Detects likely dog breed with confidence scores.
3. Generates a personalized diet plan using deterministic nutrition logic.
4. Optionally enriches diet guidance using LLM providers.
5. Supports admin controls for AI provider runtime configuration.

Current deployment intent is:
- Web on Vercel (Next.js)
- API on Railway (FastAPI)
- PostgreSQL via Supabase
- Object storage via Cloudflare R2

Important current-state note:
The repository has operational drift between documentation and implementation in some areas (auth, caching, API contracts, tests). See Section 22 for explicit details and remediation actions.

---

## 3. Product Scope

### 3.1 Core capabilities

1. Breed analysis from photo input.
2. Personalized diet target generation (calories, macros, food suggestions, feeding schedule).
3. Pet profile management.
4. Report export as PDF.
5. Admin dashboard with user stats and AI provider controls.

### 3.2 User personas

1. Pet owner
- Upload image, see breed prediction, generate diet plan.
- Manage one or more pet profiles.
- Download report for veterinary review.

2. Admin operator
- View platform usage metrics.
- View user list.
- Configure active AI provider and fallbacks.
- Run health checks and test prompts against providers.

### 3.3 Non-goals (current)

1. Veterinary diagnosis.
2. Real-time prescription workflow.
3. Billing and entitlement enforcement (subscription table exists but flow is not fully integrated).
4. Enterprise tenant isolation.

---

## 4. Current Technology Stack

### 4.1 Backend

Language and runtime:
- Python 3.12+

Framework and server:
- FastAPI
- Uvicorn

Data and ORM:
- SQLAlchemy asyncio
- asyncpg
- Alembic

Validation and serialization:
- Pydantic v2
- pydantic-settings

Authentication and crypto:
- PyJWT (HS256 in current runtime)
- passlib bcrypt

ML and inference:
- torch
- torchvision
- timm
- Pillow
- numpy

AI provider SDKs:
- google-generativeai
- openai
- anthropic

Storage and file handling:
- boto3 (S3-compatible R2)
- python-magic

Operational and utility:
- slowapi (rate limiting)
- reportlab (PDF generation)
- orjson

### 4.2 Frontend

Framework and runtime:
- Next.js 15.x
- React 18.x

Data and state:
- TanStack React Query
- Axios

UI and styling:
- Tailwind CSS
- Radix UI primitives
- Lucide icons
- Sonner and react-hot-toast
- Recharts

### 4.3 Infrastructure and delivery

1. Local development
- Docker compose for PostgreSQL and Redis
- Makefile orchestration

2. Production target
- API: Railway
- Web: Vercel
- Database: Supabase Postgres
- Object storage: Cloudflare R2

3. CI/CD
- GitHub Actions pipelines for CI, API deploy, Web deploy

---

## 5. Repository and Module Layout

Top-level:
- apps/api: FastAPI backend
- apps/web: Next.js frontend
- docs: architecture, database, deployment docs
- Makefile and docker compose files

Backend major module breakdown:
1. app/routers
- API route definitions by domain (auth, pets, predictions, diet_plans, reports, admin)

2. app/services
- Domain business logic (diet engine integration, user/pet services, storage, reporting)

3. app/ml
- Model loading, preprocessing, inference orchestration, breed label taxonomy

4. app/ai
- Provider abstraction, provider factory, fallback chain, runtime config, observability

5. app/models and app/schemas
- ORM models and API contract objects

Frontend major module breakdown:
1. src/app
- Route pages and layout groups for dashboard, auth, admin

2. src/components
- Feature components for analyze, diet, pets, admin, layout, providers

3. src/hooks
- Query and mutation wrappers around backend endpoints

4. src/lib
- API client, constants, utility functions

5. src/types
- Shared frontend TypeScript interfaces

---

## 6. System Architecture and Request Flow

### 6.1 High-level architecture

Client (Web) -> Next.js app -> FastAPI API -> Postgres + R2 + AI providers + local cache

Data and service dependencies:
1. Postgres for persistent business data.
2. Cloudflare R2 for uploaded image storage.
3. Gemini and optional OpenAI/Anthropic for AI operations.
4. Local in-process cache object for inference and AI enrichment caching.

### 6.2 Startup and runtime lifecycle

API startup behavior includes:
1. FastAPI app initialization.
2. Middleware registration (CORS, request id, security headers, error handling).
3. Anonymous user bootstrap row creation for no-auth testing flow.
4. Lazy ML model loading (first inference request loads model).

### 6.3 Inference flow (as implemented)

1. Frontend sends multipart image to predictions analyze endpoint.
2. Backend validates content type and max payload size.
3. Image bytes are validated with MIME and PIL checks.
4. SHA256 hash computed for dedupe/cache key.
5. Cache checked for existing inference result.
6. If no cache hit:
- Try Gemini vision classification.
- If Gemini unavailable, fallback to local EfficientNet inference.
7. Upload image to R2 (non-fatal if unavailable).
8. Persist upload and prediction records.
9. Cache inference result.
10. Return top prediction plus alternatives.

### 6.4 Diet generation flow (current)

1. Frontend sends request to diet generate endpoint.
2. Backend uses deterministic diet engine with fallback defaults.
3. Diet plan is generated in-memory in current anonymous mode router implementation.
4. Response is returned without persistent storage in current route implementation.

---

## 7. Backend API Reference

Base path: /api/v1

### 7.1 Auth

POST /auth/register
- Purpose: Create user account and return JWT access token.
- Request body:
  - email
  - password
  - full_name optional
- Response:
  - access_token
  - token_type
  - user_id
  - email
  - full_name
  - is_admin

POST /auth/login
- Purpose: Authenticate user and return JWT access token.
- Request body:
  - email
  - password

GET /auth/me
- Purpose: Return current authenticated user profile.

### 7.2 Pets

GET /pets
- Paginated pet list for current user.
- Query: page, page_size.

POST /pets
- Create pet profile.

GET /pets/{pet_id}
- Fetch pet by id for current user.

PATCH /pets/{pet_id}
- Partial update.

DELETE /pets/{pet_id}
- Soft delete pet.

### 7.3 Predictions

POST /predictions/analyze
- Upload image and classify breed.
- Supports optional auth (anonymous fallback user id exists).
- Rate-limited to 10/minute.

GET /predictions
- List predictions for authenticated user.
- Anonymous returns empty list.

GET /predictions/gemini-status
- Diagnostics endpoint for Gemini availability and call behavior.

### 7.4 Diet Plans

POST /diet-plans/generate
- Current behavior: anonymous in-memory generation (no persistence in this router).
- Input supports direct breed/age/weight/activity fields.

GET /diet-plans/{plan_id}
- Current behavior: always returns not found due anonymous mode implementation.

GET /diet-plans
- Current behavior: returns empty paginated list in anonymous mode implementation.

### 7.5 Reports

GET /reports/diet-plan/{plan_id}/pdf
- Generate PDF for existing plan and associated pet.
- Requires authenticated current user.

### 7.6 Admin

GET /admin/users
- List users (admin only).

GET /admin/stats
- Returns aggregate counts for users, pets, predictions, diet plans.

GET /admin/ai/config
PUT /admin/ai/config
- Runtime AI provider configuration.

GET /admin/ai/health
- Provider health checks with latency.

POST /admin/ai/test
- Test prompt against selected provider.

### 7.7 Platform health

GET /health
- Returns status, environment, version, model load status.

GET /ready
- Readiness check for DB connectivity.

---

## 8. Authentication and Authorization Model

### 8.1 Current implementation

1. HS256 JWT signed with SECRET_KEY.
2. Access tokens contain sub and email claims.
3. FastAPI dependencies enforce current user and admin role checks.
4. Frontend stores token in localStorage and injects Authorization header.

### 8.2 Anonymous product-testing mode

Current code includes anonymous behavior:
1. Anonymous user row is bootstrapped during startup.
2. Predictions endpoint accepts optional auth and can use anonymous user id.
3. AuthGuard on frontend currently renders children without token checks.
4. Sign-in and sign-up pages currently redirect to analyze page.

### 8.3 Documentation drift note

Existing docs mention Clerk/JWKS flow, but current running code path is local JWT flow. This should be reconciled by choosing one auth strategy and aligning code, docs, and deployment vars.

---

## 9. AI, ML, and Diet Engine Deep Dive

### 9.1 Breed classification strategy

Primary strategy:
- Gemini vision with JSON structured prompt and taxonomy mapping.

Fallback strategy:
- Local EfficientNet-B4 classifier using timm and PyTorch.

Model loading strategy:
- Lazy singleton model load on first inference request.
- Thread-safe lock around initialization.

### 9.2 Breed taxonomy

1. Local model class space uses 120-class index mapping.
2. Extended keys include India-specific and additional breeds for Gemini mapping.
3. Unknown keys can map by normalization/fuzzy match.

### 9.3 Diet engine formulas

RER formula:
RER = 70 * (weight_kg ^ 0.75)

DER formula:
DER = RER * life_stage_multiplier * breed_modifier

Behavior includes:
1. Life-stage and activity multipliers.
2. Breed overlays (obesity-prone, bloat risk, low purine, joint support, etc).
3. Macro splits by puppy vs adult target percentages.
4. Meal schedule generation by age and risk profile.
5. Food recommendation generation with allergy exclusions.
6. Supplement flag generation.

### 9.4 AI enrichment for diet insights

1. Optional via ai_service.
2. Sanitizes user-controlled fields before prompt construction.
3. Uses provider abstraction and optional fallback provider chain.
4. Caches enrichment result with TTL to reduce repeated provider calls.

---

## 10. Data Model and Persistence

### 10.1 Core entities

1. users
- identity, status, admin flag, soft delete support.

2. pets
- profile details, activity/life-stage context, allergies and conditions.

3. ai_predictions
- top result, alternatives, model version, latency, optional upload relation.

4. diet_plans
- generated nutritional outputs and recommendation payloads.

5. uploads
- image storage metadata, content type, checksum.

6. subscriptions
- billing shape placeholders.

7. audit_logs
- sensitive operation trace scaffolding.

### 10.2 Migrations summary

0001:
- Initial schema creation for all key tables.

0002:
- Production-hardening indexes and life_stage addition.

0003:
- AI enrichment columns for diet plans.

0004:
- ai_predictions upload_id made nullable and FK changed to ON DELETE SET NULL.

### 10.3 Indexing and query behavior

High-priority access patterns indexed include:
1. user-owned pets and prediction history.
2. pet or user diet plan history.
3. upload checksum for dedupe.

---

## 11. Frontend Architecture and UX Flows

### 11.1 Route groups

1. Public landing:
- /

2. Dashboard group:
- /dashboard
- /analyze
- /pets
- /pets/new
- /pets/{id}
- /diet-plans
- /reports

3. Auth group:
- /sign-in
- /sign-up

4. Admin group:
- /admin
- /admin/users
- /admin/ai

### 11.2 State and networking

1. React Query for query caching and invalidation.
2. Axios clients with request id and optional auth header injection.
3. Local storage token and user object utility.

### 11.3 Analyze UX flow

1. Upload image or capture camera frame.
2. Client-side optional image compression.
3. Request prediction.
4. Display top breed and alternatives.
5. Trigger diet generation CTA.

### 11.4 Layout and navigation

1. Dashboard layout with sidebar and mobile nav.
2. Admin layout with separate navigation.
3. Global toast notifications and theme provider wrappers.

---

## 12. Security, Privacy, and Hardening

### 12.1 API security controls

1. CORS allowlist and Vercel preview regex support.
2. Request id injection and response timing header.
3. Security headers:
- X-Content-Type-Options
- X-Frame-Options
- Referrer-Policy
- HSTS in production

4. Global exception handling to preserve CORS-safe error behavior.

### 12.2 Input and upload security

1. MIME verification with python-magic and PIL open checks.
2. Max upload size guard.
3. Image dimension bounds and decompression bomb guard.
4. Sanitized extension handling.

### 12.3 AI prompt safety controls

1. Prompt field sanitization and truncation.
2. Limited key set and max lengths.
3. Retry-bounded provider calls.

### 12.4 Data/privacy notes

1. Contains pet profile and user account data.
2. No medical diagnosis claim should be made.
3. PDF output includes advisory disclaimer.

---

## 13. Caching and Performance

### 13.1 Current cache implementation

Current runtime cache implementation is in-process memory TTL cache.

Implications:
1. Cache is not shared across replicas.
2. Cache is cleared on restart.
3. Not suitable as cross-instance cache.

### 13.2 Current cache usage

1. Prediction result cache by image hash.
2. AI enrichment cache by normalized input hash.

### 13.3 Performance levers

1. Client-side image compression before upload.
2. Server-side image compression before R2 storage.
3. Single-threaded ML worker to fit constrained memory environments.
4. Optional provider fallback to avoid full user failure on primary AI outage.

---

## 14. Environment Variables Reference

### 14.1 Backend

Required or commonly used:
1. ENVIRONMENT
2. DATABASE_URL
3. SECRET_KEY
4. GEMINI_API_KEY
5. AI_ENABLED
6. AI_ACTIVE_PROVIDER
7. CLOUDFLARE_R2_ACCOUNT_ID
8. CLOUDFLARE_R2_ACCESS_KEY_ID
9. CLOUDFLARE_R2_SECRET_ACCESS_KEY
10. CLOUDFLARE_R2_BUCKET_NAME
11. CLOUDFLARE_R2_ENDPOINT_URL
12. CLOUDFLARE_R2_PUBLIC_URL
13. ALLOWED_ORIGINS
14. ML_MODEL_PATH

Optional provider keys:
1. OPENAI_API_KEY
2. ANTHROPIC_API_KEY

### 14.2 Frontend

1. NEXT_PUBLIC_API_URL
2. Optional diagnostics and analytics settings as needed

---

## 15. Local Development Runbook

### 15.1 Prerequisites

1. Python 3.12+
2. Node 18+
3. Docker
4. Make

### 15.2 Setup

1. Install backend and frontend dependencies through Makefile targets.
2. Copy env templates.
3. Start local infra with docker compose dev stack.
4. Apply migrations.
5. Start API and web services.

### 15.3 Common workflows

1. Run API tests.
2. Create migration revisions.
3. Build local Docker images.
4. Clean local build caches.

---

## 16. Deployment and Operations Runbook

### 16.1 API deployment model

1. Containerized FastAPI app.
2. Startup command runs alembic upgrade head then launches uvicorn.
3. Healthcheck endpoint configured on /health.

### 16.2 Web deployment model

1. Next standalone build in production image.
2. Vercel deploy pipeline for hosted frontend.

### 16.3 Platform integration assumptions

1. Database connectivity validated by readiness probe.
2. R2 credentials required for durable image storage.
3. Gemini key required for primary AI path.

### 16.4 CI/CD overview

1. CI pipeline:
- API lint, type check, tests
- Web type check and lint

2. Deploy API pipeline:
- Test gate
- Railway deployment

3. Deploy Web pipeline:
- Typecheck and lint gate
- Vercel build and deploy

---

## 17. Testing and Quality Strategy

### 17.1 Backend tests currently present

1. auth tests
2. pets tests
3. predictions tests
4. admin tests

### 17.2 Test environment model

1. Uses sqlite async in-memory fixtures for many tests.
2. Optional integration marker available for real DB scenarios.

### 17.3 Quality risks

1. Contract drift between frontend and backend response models.
2. Some tests appear stale or mismatched with current router implementation.
3. Presence of misplaced test file content requires cleanup.

---

## 18. Observability and Incident Response

### 18.1 Logging

1. Structured JSON logging in production mode.
2. CORS trace logging around auth and preflight paths.
3. AI provider request outcome logging includes provider, latency, token usage.

### 18.2 Health checks

1. /health for app status and model status field.
2. /ready for database readiness.

### 18.3 Suggested SLO baselines

1. API availability: 99.5% minimum target.
2. Analyze endpoint p95 latency: <= 2500 ms target.
3. Diet generation endpoint p95 latency: <= 800 ms target.

### 18.4 Incident runbook (recommended)

P1 API outage checklist:
1. Check /health and /ready.
2. Validate DB connectivity and credentials.
3. Validate container logs for startup migration failures.
4. Confirm R2 and AI provider keys are still valid.
5. Rollback to last known good deployment if needed.

P2 model/AI degradation checklist:
1. Check Gemini status endpoint and provider health endpoint.
2. Validate fallback provider readiness.
3. Confirm local model load status.
4. Temporarily disable AI enrichment if non-critical path is failing.

---

## 19. Release Management

### 19.1 Release checklist

1. Run backend tests and static checks.
2. Run frontend typecheck and lint.
3. Validate migration scripts and backward compatibility.
4. Verify health and readiness behavior in staging.
5. Verify critical user journeys:
- analyze image
- generate diet
- manage pets
- download report
- admin ai config

### 19.2 Change log template

For each release capture:
1. Scope and objective.
2. DB migration impact.
3. API contract changes.
4. Frontend route or UX changes.
5. Rollback approach.
6. Monitoring alerts to watch post-release.

---

## 20. Governance and Ownership

Suggested ownership model:
1. Product owner: roadmap, prioritization, acceptance.
2. Backend owner: API contracts, data model, service reliability.
3. Frontend owner: UI flows, state model, contract adherence.
4. DevOps owner: deployment pipeline, infra health, secrets governance.
5. QA owner: test strategy, regression suite, release signoff.

RACI recommendation for critical domains:
1. Auth strategy and migration: Product + Backend + Security
2. API contract versioning: Backend + Frontend
3. Data migrations: Backend + DevOps
4. Incident management: DevOps + Backend

---

## 21. API Contract Canonical Model (Recommended)

To reduce drift, define these canonical patterns:

1. Pagination standard
- fields: items, total, page, page_size, pages
- frontend types and hooks must mirror this exactly

2. Admin stats standard
- fields: users, pets, predictions, diet_plans
- frontend mapping layer may convert to display naming if needed

3. Report download path standard
- keep one route format only and remove all stale client usages

4. Auth strategy decision
- either Clerk end-to-end or local JWT end-to-end
- avoid mixed docs and partial implementation

---

## 22. Known Gaps and Remediation Plan

This section is intended to stay live and updated.

### 22.1 High priority gaps

1. Auth documentation and runtime mismatch
- Docs describe Clerk flow; runtime uses local HS256 JWT.
- Action: choose single auth architecture and align backend, frontend, env docs, and tests.

2. Diet plan persistence mismatch
- Dedicated diet service includes persistence logic, but current router is anonymous in-memory mode.
- Action: decide whether to restore persisted user flow or keep anonymous product mode with explicit product positioning.

3. Frontend/backend contract mismatches
- Admin stats key names differ.
- Admin users query params differ (limit/offset vs page/page_size).
- Pagination type differs in frontend and backend.
- Reports route path differs.
- Action: normalize all contracts and add contract tests.

4. Duplicate admin route declarations
- users and stats handlers are duplicated in the same router file.
- Action: remove duplicate definitions and keep one canonical implementation.

5. Misplaced test file
- apps/api/tests/test_diet.py currently contains frontend redirect component code.
- Action: replace with real diet API tests and investigate how corruption occurred.

### 22.2 Medium priority gaps

1. Cache architecture drift
- Deployment docs discuss Redis, runtime cache is currently in-memory.
- Action: either implement Redis-backed cache abstraction or update docs and expected behavior.

2. Root-level stray frontend file
- page.tsx exists at repo root and appears unrelated to active web app structure.
- Action: confirm intent and remove or relocate as needed.

3. Readiness docs drift
- Some docs reference cache/model checks in readiness output while current readiness checks only DB.
- Action: update docs or expand readiness implementation.

### 22.3 Suggested remediation sequence

Phase 1 (stabilize contracts):
1. Fix API route and response shape mismatches.
2. Remove duplicate routes.
3. Repair broken test file and baseline test suite.

Phase 2 (auth and product mode alignment):
1. Finalize auth strategy.
2. Align frontend guards and auth pages.
3. Align docs and deployment vars.

Phase 3 (operational hardening):
1. Decide cache strategy and implement consistently.
2. Tighten readiness checks and observability metrics.
3. Add integration tests for critical paths.

---

## 23. Future Roadmap (Proposed)

### 23.1 Product

1. Vet collaboration workflow and shared report links.
2. Pet progress tracking over time.
3. Plan history diff and feeding adherence logging.
4. Regionalized food catalog recommendations.

### 23.2 Engineering

1. Contract-first API with generated clients.
2. OpenAPI-driven integration tests.
3. Dedicated staging environment with smoke suite.
4. Role-based authorization expansion.

### 23.3 AI/ML

1. Fine-tuned production model registry and versioning strategy.
2. Better confidence calibration and low-confidence handling UX.
3. Human feedback loop for prediction correction.
4. Prompt/evaluation framework for AI enrichment quality.

---

## 24. Glossary

1. RER: Resting Energy Requirement.
2. DER: Daily Energy Requirement.
3. LLM: Large Language Model.
4. TTL: Time to Live for cache entries.
5. HSTS: HTTP Strict Transport Security.
6. CORS: Cross-Origin Resource Sharing.
7. P95 latency: 95th percentile request response time.

---

## 25. Appendix A - Example Payloads

### 25.1 Register request

{
  "email": "owner@example.com",
  "password": "strong-password",
  "full_name": "Pet Owner"
}

### 25.2 Analyze response (shape example)

{
  "id": "prediction-uuid",
  "user_id": "user-uuid",
  "pet_id": null,
  "top_breed": "labrador_retriever",
  "top_confidence": 0.94,
  "all_predictions": [
    { "breed": "labrador_retriever", "display_name": "Labrador Retriever", "confidence": 0.94 },
    { "breed": "golden_retriever", "display_name": "Golden Retriever", "confidence": 0.04 }
  ],
  "model_version": "gemini-vision-2.5-flash",
  "inference_time_ms": 0,
  "image_url": "https://example",
  "created_at": "2026-05-27T12:00:00Z"
}

### 25.3 Diet generation request (anonymous mode)

{
  "breed": "labrador_retriever",
  "age_months": 36,
  "weight_kg": 28.0,
  "activity_level": "moderate",
  "is_neutered": true,
  "sex": "male",
  "allergies": ["chicken"],
  "health_conditions": ["overweight"]
}

---

## 26. Appendix B - Source of Truth Policy (Recommended)

To avoid future drift, adopt the following hierarchy:

1. Running API contracts in backend schemas and routers are the technical source of truth.
2. Frontend generated types or shared contract package should mirror backend contracts.
3. Confluence pages should reference versioned release notes and contract snapshots.
4. Deployment docs should only include currently supported env variables and active architecture.

---

End of document.
