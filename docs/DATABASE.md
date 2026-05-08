# Database Schema

## Entity Relationship Overview

```
users ──< pets ──< ai_predictions
      │          └──< diet_plans
      │
      └──< subscriptions
      └──< audit_logs
```

---

## Tables

### users

Synced from Clerk via webhook. Source of truth for auth is Clerk.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| clerk_user_id | VARCHAR(255) UNIQUE | Clerk's user_id |
| email | VARCHAR(255) UNIQUE | |
| full_name | VARCHAR(255) | |
| avatar_url | TEXT | |
| is_admin | BOOLEAN | Default false |
| is_active | BOOLEAN | Default true |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |
| deleted_at | TIMESTAMPTZ | Soft delete |

### pets

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users.id | |
| name | VARCHAR(100) | |
| breed | VARCHAR(100) | |
| age_months | INTEGER | |
| weight_kg | DECIMAL(5,2) | |
| sex | ENUM | male/female |
| is_neutered | BOOLEAN | |
| activity_level | ENUM | sedentary/light/moderate/active/very_active |
| allergies | JSONB | Array of strings |
| health_conditions | JSONB | Array of strings |
| notes | TEXT | |
| avatar_url | TEXT | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |
| deleted_at | TIMESTAMPTZ | |

### ai_predictions

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users.id | |
| pet_id | UUID FK → pets.id NULLABLE | |
| upload_id | UUID FK → uploads.id | |
| top_breed | VARCHAR(100) | Highest confidence breed |
| top_confidence | DECIMAL(5,4) | 0.0 - 1.0 |
| all_predictions | JSONB | [{breed, confidence}] top-5 |
| model_version | VARCHAR(50) | e.g. "efficientnet_b4_v1.2" |
| inference_time_ms | INTEGER | |
| created_at | TIMESTAMPTZ | |

### diet_plans

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| pet_id | UUID FK → pets.id | |
| user_id | UUID FK → users.id | |
| prediction_id | UUID FK → ai_predictions.id NULLABLE | |
| breed | VARCHAR(100) | |
| age_months | INTEGER | |
| weight_kg | DECIMAL(5,2) | |
| activity_level | ENUM | |
| daily_calories | INTEGER | kcal/day |
| protein_g | DECIMAL(6,2) | grams/day |
| fat_g | DECIMAL(6,2) | grams/day |
| carbs_g | DECIMAL(6,2) | grams/day |
| meals_per_day | INTEGER | |
| food_recommendations | JSONB | [{name, amount_g, notes}] |
| foods_to_avoid | JSONB | Array of strings |
| supplement_flags | JSONB | Array of strings |
| feeding_schedule | JSONB | [{time, amount_g}] |
| notes | TEXT | |
| engine_version | VARCHAR(50) | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### uploads

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users.id | |
| r2_key | VARCHAR(512) | Cloudflare R2 object key |
| r2_bucket | VARCHAR(255) | |
| original_filename | VARCHAR(255) | |
| content_type | VARCHAR(100) | |
| size_bytes | INTEGER | |
| sha256_hash | CHAR(64) | For deduplication |
| created_at | TIMESTAMPTZ | |

### subscriptions

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users.id | |
| plan | ENUM | free/pro/premium |
| status | ENUM | active/cancelled/past_due |
| stripe_subscription_id | VARCHAR(255) | |
| stripe_customer_id | VARCHAR(255) | |
| current_period_start | TIMESTAMPTZ | |
| current_period_end | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

### audit_logs

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK NULLABLE | |
| action | VARCHAR(100) | e.g. "pet.delete", "admin.user_ban" |
| resource_type | VARCHAR(50) | e.g. "pet", "user" |
| resource_id | UUID NULLABLE | |
| metadata | JSONB | Extra context |
| ip_address | INET | |
| user_agent | TEXT | |
| created_at | TIMESTAMPTZ | |

---

## Indexes

```sql
-- Performance indexes
CREATE INDEX idx_pets_user_id ON pets(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_predictions_user_id ON ai_predictions(user_id);
CREATE INDEX idx_predictions_pet_id ON ai_predictions(pet_id);
CREATE INDEX idx_diet_plans_pet_id ON diet_plans(pet_id);
CREATE INDEX idx_uploads_sha256 ON uploads(sha256_hash);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- Unique constraints
CREATE UNIQUE INDEX idx_users_clerk_id ON users(clerk_user_id);
CREATE UNIQUE INDEX idx_subscriptions_user ON subscriptions(user_id) WHERE status = 'active';
```
