// --- Shared ---
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ApiError {
  detail: string;
  status_code?: number;
}

// --- User ---
export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// --- Pet ---
export type ActivityLevel = "sedentary" | "light" | "moderate" | "active" | "very_active";
export type LifeStage = "puppy" | "adult" | "senior";
export type Sex = "male" | "female" | "male_neutered" | "female_spayed";

export interface Pet {
  id: string;
  user_id: string;
  name: string;
  breed: string | null;
  age_months: number | null;
  weight_kg: number | null;
  sex: Sex | null;
  life_stage: LifeStage;
  activity_level: ActivityLevel;
  allergies: string[];
  health_conditions: string[];
  is_pregnant: boolean;
  is_lactating: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface PetCreate {
  name: string;
  breed?: string;
  age_months?: number;
  weight_kg?: number;
  sex?: Sex;
  life_stage?: LifeStage;
  activity_level?: ActivityLevel;
  allergies?: string[];
  health_conditions?: string[];
  is_pregnant?: boolean;
  is_lactating?: boolean;
  notes?: string;
}

// --- Prediction ---
export interface BreedPrediction {
  breed: string;
  confidence: number;
  display_name: string;
  size: string;
}

export interface Prediction {
  id: string;
  pet_id: string | null;
  top_breed: string;
  top_confidence: number;
  all_predictions: BreedPrediction[];
  model_version: string;
  inference_time_ms: number;
  cached: boolean;
  created_at: string;
}

// --- Diet Plan ---
export interface FoodItem {
  name: string;
  serving_size?: string;
  amount_g?: number;
  frequency?: string;
  category?: string;
  notes?: string;
}

export interface FeedingScheduleItem {
  meal?: string;
  meal_name?: string;
  time?: string;
  time_suggestion?: string;
  calories?: number;
  amount_kcal?: number;
  portion?: string;
  amount_g?: number;
}

export interface DietPlan {
  id: string;
  pet_id: string;
  user_id: string;
  prediction_id: string | null;
  breed: string;
  age_months: number;
  weight_kg: number;
  activity_level: string;
  daily_calories: number;
  protein_g: number;
  fat_g: number;
  carbs_g: number;
  meals_per_day: number;
  food_recommendations: FoodItem[];
  foods_to_avoid: string[];
  supplement_flags: string[];
  feeding_schedule: FeedingScheduleItem[];
  notes?: string | null;
  special_notes?: string[];
  engine_version: string;
  ai_insights?: Record<string, unknown> | null;
  ai_provider_used?: string | null;
  created_at: string;
  updated_at: string;
}

export interface GenerateDietPlanRequest {
  pet_id?: string;
  prediction_id?: string;
  breed?: string;
  age_months?: number;
  weight_kg?: number;
  activity_level?: string;
}
