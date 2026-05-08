# System Architecture

## Overview

Dog Breed Diet Planner is a mobile-first SaaS platform with a clear separation of concerns:

```
Browser/Mobile
      │
      ▼
  Vercel (Next.js)
      │  HTTPS + Clerk JWT
      ▼
 Railway (FastAPI)
      │
   ┌──┴──────────────┐
   │                  │
PostgreSQL         Redis (Upstash)
                      │
               Cloudflare R2 (images)
```

---

## Request Flow

### Image Analysis Flow

```
1. User selects image (or captures via camera)
2. Client validates: MIME type, file size ≤ 10MB
3. POST /api/v1/predictions/analyze  (multipart/form-data)
4. Backend:
   a. Validate MIME type with python-magic (server-side)
   b. Upload original to Cloudflare R2
   c. Preprocess image (resize to 380×380, normalize)
   d. Run EfficientNet-B4 inference (CPU, ~700ms)
   e. Check Redis cache (sha256 of image bytes → result)
   f. Store prediction record in PostgreSQL
5. Return top-5 breeds + confidence scores
6. Client renders breed card + triggers diet plan generation
```

### Diet Plan Flow

```
1. POST /api/v1/diet-plans/generate
   Body: { pet_id, breed, age_months, weight_kg, activity_level, allergies[], health_conditions[] }
2. Backend diet engine:
   a. Calculate RER = 70 × weight_kg^0.75
   b. Look up life-stage multiplier
   c. Apply breed-specific health overlays
   d. Calculate DER and macronutrient targets
   e. Generate food recommendations list
   f. Apply allergy exclusions
3. Persist DietPlan record
4. Return structured diet plan
```

### Auth Flow

```
1. User signs up/in via Clerk (frontend)
2. Clerk issues signed JWT
3. Frontend sends JWT in Authorization: Bearer header
4. FastAPI auth middleware:
   a. Verify JWT signature via Clerk JWKS endpoint
   b. Extract clerk_user_id
   c. Upsert user in local PostgreSQL (sync from Clerk)
5. Request proceeds with authenticated user context
```

---

## AI/ML Architecture

### Model: EfficientNet-B4

- **Why B4 over B0/MobileNetV2**: ~85% top-5 accuracy on Stanford Dogs vs ~71% MobileNetV2
- **Why not B7**: 3× slower inference, diminishing accuracy returns for dog breeds
- **Input**: 380×380 RGB, ImageNet normalization
- **Output**: 120 logits → softmax → top-5 predictions with confidence
- **Inference time**: ~700ms CPU, ~80ms GPU
- **Loading**: Singleton model instance loaded at startup, thread-safe

### Inference Pipeline

```python
ImageBytes
    → MIMEValidator
    → ImagePreprocessor (decode, resize, normalize, tensorize)
    → BreedClassifier.predict()
    → PostProcessor (labels, confidence formatting)
    → RedisCache.store(sha256_hash, result)
    → PredictionRecord (PostgreSQL)
```

### Fine-tuning

The model is designed for fine-tuning on Stanford Dogs Dataset (120 classes):
- Base: `timm.create_model("efficientnet_b4", pretrained=True)`
- Replace classifier head: `num_classes=120`
- Training: AdamW, cosine LR schedule, label smoothing 0.1
- Augmentation: Random crop, horizontal flip, color jitter, MixUp

---

## Diet Recommendation Engine

Based on NRC (National Research Council) and AAFCO nutritional guidelines.

### Caloric Calculation

```
RER (kcal/day) = 70 × body_weight_kg^0.75
DER (kcal/day) = RER × life_stage_multiplier

Life Stage Multipliers:
  Puppy < 4 months:     3.0
  Puppy 4-12 months:    2.0
  Intact adult:         1.8
  Neutered adult:       1.6
  Active adult:         2.0-5.0 (working dogs)
  Senior (>7 years):    1.2-1.4
  Obese (weight loss):  0.8 × RER
```

### Macronutrient Targets (per AAFCO)

| Nutrient | Adult | Puppy |
|---|---|---|
| Protein | 18-25% kcal | 22-32% kcal |
| Fat | 10-15% kcal | 8-17% kcal |
| Fiber | 2-5% DM | 2-5% DM |

### Breed-Specific Overlays

- German Shepherd: +glucosamine/chondroitin supplement flag
- Labrador/Beagle: obesity_prone=True → reduce multiplier by 10%
- Great Dane/Saint Bernard: bloat_risk=True → 3 small meals/day
- Dalmatian: low_purine_diet=True → exclude high-purine proteins
- Brachycephalic breeds: avoid high-fat diets, smaller kibble

---

## Database Architecture

See [DATABASE.md](DATABASE.md) for full schema.

Key design decisions:
- **UUID primary keys** (not sequential integers) — no enumeration attacks
- **Soft deletes** on pets and users (deleted_at timestamp)
- **JSON columns** for flexible fields (allergies, health_conditions, food_list)
- **Audit log** for all sensitive operations (admin actions, prediction usage)
- **Subscriptions table** is future-ready but not blocking MVP

---

## Security Architecture

- **Auth**: Clerk JWT RS256, verified via JWKS endpoint (no shared secret)
- **Rate limiting**: SlowAPI — 60 req/min per user, 10 req/min for /analyze
- **Upload validation**: MIME type check with python-magic (not just extension)
- **File size**: Hard 10MB limit before processing
- **SQL injection**: SQLAlchemy ORM only, no raw SQL
- **CORS**: Whitelist of allowed origins only
- **Secrets**: Environment variables only, never in code
- **XSS**: CSP headers via Next.js config, React's inherent escaping
- **HTTPS**: Enforced at Vercel + Railway platform level

---

## Infrastructure & Cost

### Free Tier Baseline

| Service | Free Tier | Paid Trigger |
|---|---|---|
| Vercel | 100GB bandwidth, unlimited deploys | > 100GB/month |
| Railway | $5/month hobby plan | - |
| Upstash Redis | 10K req/day, 256MB | > 10K req/day |
| Cloudflare R2 | 10GB storage, 1M writes | > 10GB |
| Clerk | 10K MAU | > 10K users |
| Sentry | 5K events/month | > 5K events |
| PostHog | 1M events/month | > 1M events |

**Estimated monthly cost at launch: ~$5-10/month**

### Scale Path

1. Move inference to GPU (Replicate/Modal) when p95 latency > 2s
2. Add connection pooling (PgBouncer) when DB connections > 80%
3. Add CDN image transforms (Cloudflare) when image egress > 50GB
4. Move to dedicated Railway plan when CPU consistently > 70%
