export const ACTIVITY_LEVELS = [
  { value: "sedentary", label: "Sedentary (mostly resting)" },
  { value: "low", label: "Low (short daily walks)" },
  { value: "moderate", label: "Moderate (1-2 hrs activity/day)" },
  { value: "high", label: "High (2+ hrs vigorous activity)" },
  { value: "very_high", label: "Very High (working/sport dog)" },
] as const;

export const LIFE_STAGES = [
  { value: "puppy", label: "Puppy (< 1 year)" },
  { value: "adult", label: "Adult" },
  { value: "senior", label: "Senior (7+ years)" },
] as const;

export const SEX_OPTIONS = [
  { value: "male", label: "Male (intact)" },
  { value: "female", label: "Female (intact)" },
  { value: "male_neutered", label: "Male (neutered)" },
  { value: "female_spayed", label: "Female (spayed)" },
] as const;

export const BREED_SIZES: Record<string, string> = {
  toy: "Toy (< 5 kg)",
  small: "Small (5-10 kg)",
  medium: "Medium (11-25 kg)",
  large: "Large (26-44 kg)",
  giant: "Giant (45+ kg)",
};

export const MAX_UPLOAD_SIZE_MB = 10;
export const ACCEPTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];
