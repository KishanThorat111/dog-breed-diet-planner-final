"""
Diet Recommendation Engine
==========================
Science-based personalized dog diet planning using:
  - NRC (National Research Council) Nutrient Requirements of Dogs
  - AAFCO nutritional guidelines
  - Breed-specific health overlays

Algorithm:
  1. Calculate Resting Energy Requirement (RER): 70 × BW(kg)^0.75
  2. Determine life-stage multiplier
  3. Apply breed-specific modifiers (obesity-prone → reduce by 10%)
  4. Calculate Daily Energy Requirement (DER) = RER × multiplier
  5. Distribute macronutrients per AAFCO minimum guidelines
  6. Build food recommendations and feeding schedule
  7. Apply allergy exclusions
  8. Flag supplement recommendations
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal

ENGINE_VERSION = "diet_engine_v1.2"

# ─────────────────────────────────────────────
# Life-Stage Multipliers
# ─────────────────────────────────────────────
ACTIVITY_MULTIPLIERS: dict[str, float] = {
    "sedentary": 1.2,
    "light": 1.4,
    "moderate": 1.6,
    "active": 2.0,
    "very_active": 3.0,
}

# ─────────────────────────────────────────────
# Breed-specific overlays
# ─────────────────────────────────────────────
@dataclass
class BreedOverlay:
    obesity_prone: bool = False
    bloat_risk: bool = False           # → multiple small meals
    low_purine: bool = False           # Dalmatian → avoid organ meats
    joint_support: bool = False        # Large/giant breeds → glucosamine
    heart_support: bool = False        # Cavalier KCS, Boxers
    skin_support: bool = False         # Retrievers → omega-3
    brachycephalic: bool = False       # → smaller kibble, avoid high fat
    caloric_modifier: float = 1.0      # Multiply DER by this factor


BREED_OVERLAYS: dict[str, BreedOverlay] = {
    # Obesity-prone
    "labrador_retriever":   BreedOverlay(obesity_prone=True, caloric_modifier=0.9, skin_support=True),
    "beagle":               BreedOverlay(obesity_prone=True, caloric_modifier=0.9),
    "cocker_spaniel":       BreedOverlay(obesity_prone=True, skin_support=True),
    "basset":               BreedOverlay(obesity_prone=True, caloric_modifier=0.9, joint_support=True),
    "pug":                  BreedOverlay(obesity_prone=True, brachycephalic=True, caloric_modifier=0.85),
    "french_bulldog":       BreedOverlay(obesity_prone=True, brachycephalic=True, caloric_modifier=0.85),
    "english_springer":     BreedOverlay(obesity_prone=True),

    # Bloat risk (giant/deep-chested)
    "great_dane":           BreedOverlay(bloat_risk=True, joint_support=True, caloric_modifier=1.0),
    "saint_bernard":        BreedOverlay(bloat_risk=True, joint_support=True),
    "irish_wolfhound":      BreedOverlay(bloat_risk=True, joint_support=True, heart_support=True),
    "weimaraner":           BreedOverlay(bloat_risk=True),
    "doberman":             BreedOverlay(bloat_risk=True, heart_support=True),
    "rottweiler":           BreedOverlay(bloat_risk=True, joint_support=True, obesity_prone=True),
    "german_shepherd":      BreedOverlay(bloat_risk=True, joint_support=True),
    "boxer":                BreedOverlay(bloat_risk=True, heart_support=True),

    # Low-purine
    "dalmatian":            BreedOverlay(low_purine=True),

    # Joint support (large/giant breeds)
    "golden_retriever":     BreedOverlay(joint_support=True, skin_support=True, obesity_prone=True),
    "bernese_mountain_dog": BreedOverlay(joint_support=True),
    "newfoundland":         BreedOverlay(joint_support=True, obesity_prone=True),
    "great_pyrenees":       BreedOverlay(joint_support=True),
    "leonberg":             BreedOverlay(joint_support=True),
    "tibetan_mastiff":      BreedOverlay(joint_support=True),
    "bull_mastiff":         BreedOverlay(joint_support=True, obesity_prone=True),
    "malamute":             BreedOverlay(joint_support=True, obesity_prone=True),
    "siberian_husky":       BreedOverlay(skin_support=True),

    # Heart support
    "cavalier": BreedOverlay(heart_support=True),

    # Skin/Coat
    "irish_setter":         BreedOverlay(skin_support=True),
    "chesapeake_bay_retriever": BreedOverlay(skin_support=True),
}


# ─────────────────────────────────────────────
# Food Database (per AAFCO nutritional guidelines)
# ─────────────────────────────────────────────
@dataclass
class FoodItem:
    name: str
    category: str            # protein | carb | vegetable | fat | supplement
    kcal_per_100g: float
    protein_pct: float       # grams protein per 100g
    fat_pct: float
    notes: str = ""
    is_high_purine: bool = False
    is_allergen: bool = False
    allergen_tags: list[str] = field(default_factory=list)  # grain, chicken, beef, fish, dairy


FOOD_DATABASE: list[FoodItem] = [
    # Proteins
    FoodItem("Chicken breast (cooked)", "protein", 165, 31, 3.6, allergen_tags=["chicken"]),
    FoodItem("Turkey breast (cooked)", "protein", 135, 30, 1.0, allergen_tags=["turkey"]),
    FoodItem("Salmon (cooked)", "protein", 208, 20, 13, notes="Rich in omega-3", allergen_tags=["fish"]),
    FoodItem("Beef (lean, cooked)", "protein", 215, 26, 12, is_high_purine=True, allergen_tags=["beef"]),
    FoodItem("Lamb (cooked)", "protein", 294, 25, 21, allergen_tags=["lamb"]),
    FoodItem("Egg (cooked)", "protein", 155, 13, 11, allergen_tags=["egg"]),
    FoodItem("Cottage cheese (low fat)", "protein", 72, 11, 1.0, allergen_tags=["dairy"]),
    FoodItem("Sardines (canned in water)", "protein", 208, 24, 11, notes="Excellent omega-3 source", allergen_tags=["fish"]),

    # Carbohydrates
    FoodItem("Brown rice (cooked)", "carb", 112, 2.3, 0.8, allergen_tags=["grain"]),
    FoodItem("Sweet potato (cooked)", "carb", 86, 1.6, 0.1, notes="High in beta-carotene"),
    FoodItem("Oatmeal (cooked)", "carb", 71, 2.5, 1.4, allergen_tags=["grain"]),
    FoodItem("Quinoa (cooked)", "carb", 120, 4.4, 1.9),
    FoodItem("Pumpkin (plain, cooked)", "carb", 26, 1.0, 0.1, notes="Good for digestion"),

    # Vegetables
    FoodItem("Carrots (cooked)", "vegetable", 35, 0.8, 0.2),
    FoodItem("Green beans (cooked)", "vegetable", 35, 2.0, 0.2, notes="Low-calorie filler"),
    FoodItem("Spinach (cooked)", "vegetable", 23, 3.0, 0.4, notes="Iron-rich"),
    FoodItem("Broccoli (cooked)", "vegetable", 35, 2.4, 0.4),
    FoodItem("Zucchini (cooked)", "vegetable", 17, 1.2, 0.3),

    # Healthy fats
    FoodItem("Fish oil", "fat", 900, 0, 100, notes="Omega-3 supplementation"),
    FoodItem("Flaxseed oil", "fat", 884, 0, 100, notes="Plant-based omega-3"),
]

# Index for allergy exclusion lookups
_FOOD_BY_ALLERGEN: dict[str, list[FoodItem]] = {}
for _fi in FOOD_DATABASE:
    for _tag in _fi.allergen_tags:
        _FOOD_BY_ALLERGEN.setdefault(_tag, []).append(_fi)


# ─────────────────────────────────────────────
# Engine Output
# ─────────────────────────────────────────────
@dataclass
class DietPlanResult:
    breed: str
    age_months: int
    weight_kg: float
    activity_level: str
    daily_calories: int
    protein_g: float
    fat_g: float
    carbs_g: float
    meals_per_day: int
    food_recommendations: list[dict]
    foods_to_avoid: list[str]
    supplement_flags: list[str]
    feeding_schedule: list[dict]
    notes: str
    engine_version: str


# ─────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────
class DietEngine:
    """
    Stateless diet calculation engine.
    Call generate() with pet parameters → DietPlanResult.
    """

    def generate(
        self,
        breed: str,
        age_months: int,
        weight_kg: float,
        activity_level: str,
        is_neutered: bool = True,
        sex: str = "male",
        allergies: list[str] | None = None,
        health_conditions: list[str] | None = None,
    ) -> DietPlanResult:
        allergies = [a.lower() for a in (allergies or [])]
        health_conditions = [h.lower() for h in (health_conditions or [])]

        # 1. Resting Energy Requirement (RER)
        rer = 70.0 * (weight_kg ** 0.75)

        # 2. Life-stage multiplier
        multiplier = self._life_stage_multiplier(age_months, is_neutered, activity_level)

        # 3. Breed-specific modifier
        overlay = BREED_OVERLAYS.get(breed, BreedOverlay())
        if overlay.obesity_prone:
            multiplier *= 0.9  # Reduce 10% for obesity-prone breeds
        if "obese" in health_conditions or "overweight" in health_conditions:
            multiplier = min(multiplier, 1.0)  # Cap at RER for weight loss

        # 4. Daily Energy Requirement
        der = rer * multiplier * overlay.caloric_modifier
        daily_calories = max(int(round(der)), 100)  # Floor at 100 kcal

        # 5. Macronutrient distribution (per AAFCO)
        is_puppy = age_months < 12
        protein_pct, fat_pct = self._macronutrient_split(is_puppy)
        carb_pct = 1.0 - protein_pct - fat_pct

        # Kcal from each macro
        protein_kcal = daily_calories * protein_pct
        fat_kcal = daily_calories * fat_pct
        carb_kcal = daily_calories * carb_pct

        # Convert to grams (protein: 3.5 kcal/g, fat: 8.5 kcal/g, carbs: 3.5 kcal/g)
        protein_g = round(protein_kcal / 3.5, 1)
        fat_g = round(fat_kcal / 8.5, 1)
        carbs_g = round(carb_kcal / 3.5, 1)

        # 6. Meals per day
        meals_per_day = self._meals_per_day(age_months, overlay.bloat_risk, weight_kg)

        # 7. Food recommendations
        food_recs = self._build_food_recommendations(
            daily_calories, protein_g, fat_g, carbs_g,
            allergies, overlay, health_conditions
        )

        # 8. Foods to avoid
        foods_to_avoid = self._build_avoid_list(allergies, overlay)

        # 9. Supplements
        supplements = self._build_supplements(overlay, health_conditions, is_puppy)

        # 10. Feeding schedule
        feeding_schedule = self._build_schedule(daily_calories, meals_per_day)

        # 11. Notes
        notes = self._build_notes(overlay, is_puppy, health_conditions)

        return DietPlanResult(
            breed=breed,
            age_months=age_months,
            weight_kg=weight_kg,
            activity_level=activity_level,
            daily_calories=daily_calories,
            protein_g=protein_g,
            fat_g=fat_g,
            carbs_g=carbs_g,
            meals_per_day=meals_per_day,
            food_recommendations=food_recs,
            foods_to_avoid=foods_to_avoid,
            supplement_flags=supplements,
            feeding_schedule=feeding_schedule,
            notes=notes,
            engine_version=ENGINE_VERSION,
        )

    # ─────────────────────────────────────────
    # Private helpers
    # ─────────────────────────────────────────

    def _life_stage_multiplier(self, age_months: int, is_neutered: bool, activity_level: str) -> float:
        if age_months < 4:
            return 3.0
        if age_months < 12:
            return 2.0
        if age_months >= 84:  # Senior: 7+ years
            base = 1.2
        elif is_neutered:
            base = 1.6
        else:
            base = 1.8
        activity_modifier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.6)
        # Blend base with activity for adult dogs
        return max(base, activity_modifier * 0.9)

    def _macronutrient_split(self, is_puppy: bool) -> tuple[float, float]:
        """Returns (protein_fraction, fat_fraction) of total kcal."""
        if is_puppy:
            return 0.28, 0.17  # AAFCO puppy: 22% DM protein min, 8.5% DM fat min
        return 0.22, 0.13      # AAFCO adult: 18% DM protein min, 5.5% DM fat min

    def _meals_per_day(self, age_months: int, bloat_risk: bool, weight_kg: float) -> int:
        if age_months < 4:
            return 4
        if age_months < 6:
            return 3
        if bloat_risk or weight_kg > 40:
            return 3  # Giant/bloat-risk breeds should never eat one large meal
        return 2

    def _build_food_recommendations(
        self,
        daily_calories: int,
        protein_g: float,
        fat_g: float,
        carbs_g: float,
        allergies: list[str],
        overlay: BreedOverlay,
        health_conditions: list[str],
    ) -> list[dict]:
        """Build proportional food list, excluding allergens."""
        excluded_foods: set[str] = set()
        for allergen in allergies:
            for fi in _FOOD_BY_ALLERGEN.get(allergen, []):
                excluded_foods.add(fi.name)
        if overlay.low_purine:
            for fi in FOOD_DATABASE:
                if fi.is_high_purine:
                    excluded_foods.add(fi.name)

        recs = []

        # Select proteins
        proteins = [f for f in FOOD_DATABASE if f.category == "protein" and f.name not in excluded_foods]
        if proteins:
            primary_protein = proteins[0]
            # Amount to hit ~70% of protein target from primary protein
            amount_g = round((protein_g * 0.7 * 100) / primary_protein.protein_pct, 0)
            recs.append({
                "name": primary_protein.name,
                "amount_g": amount_g,
                "category": "protein",
                "notes": primary_protein.notes or "Primary protein source",
            })
            if len(proteins) > 1:
                secondary = proteins[1]
                amount_g2 = round((protein_g * 0.3 * 100) / secondary.protein_pct, 0)
                recs.append({
                    "name": secondary.name,
                    "amount_g": amount_g2,
                    "category": "protein",
                    "notes": secondary.notes or "Secondary protein source",
                })

        # Select carbohydrates
        carbs = [f for f in FOOD_DATABASE if f.category == "carb" and f.name not in excluded_foods]
        if carbs:
            primary_carb = carbs[0]
            # Amount to hit carb target
            amount_g = round((carbs_g * 100) / primary_carb.kcal_per_100g * 3.5, 0)
            recs.append({
                "name": primary_carb.name,
                "amount_g": max(amount_g, 50),
                "category": "carb",
                "notes": primary_carb.notes or "Primary carbohydrate source",
            })

        # Add vegetable (5-10% of plate)
        vegs = [f for f in FOOD_DATABASE if f.category == "vegetable"]
        if vegs:
            recs.append({
                "name": vegs[0].name,
                "amount_g": 30,
                "category": "vegetable",
                "notes": "Fiber and micronutrients",
            })

        # Omega-3 fat if skin support needed
        if overlay.skin_support:
            recs.append({
                "name": "Fish oil",
                "amount_g": round(weight_kg * 0.1, 1),  # ~100mg EPA/DHA per kg BW
                "category": "fat",
                "notes": "Skin and coat support — omega-3 fatty acids",
            })

        return recs

    def _build_avoid_list(self, allergies: list[str], overlay: BreedOverlay) -> list[str]:
        avoid = [
            "Chocolate",
            "Grapes and raisins",
            "Onions and garlic",
            "Xylitol (artificial sweetener)",
            "Macadamia nuts",
            "Avocado",
            "Alcohol",
            "Caffeine",
            "Raw dough (yeast)",
        ]
        for allergen in allergies:
            avoid.append(f"All {allergen}-containing foods (allergen)")
        if overlay.low_purine:
            avoid.extend(["Organ meats (liver, kidney)", "Sardines in oil", "Anchovies"])
        if overlay.brachycephalic:
            avoid.append("High-fat foods (increases respiratory stress)")
        return avoid

    def _build_supplements(
        self, overlay: BreedOverlay, health_conditions: list[str], is_puppy: bool
    ) -> list[str]:
        supplements = []
        if overlay.joint_support or "arthritis" in health_conditions or "hip dysplasia" in health_conditions:
            supplements.append("Glucosamine (20-25 mg/kg/day) + Chondroitin (5 mg/kg/day)")
        if overlay.heart_support or "heart disease" in health_conditions:
            supplements.append("Taurine (500mg/day) — consult your vet for DCM risk assessment")
            supplements.append("L-Carnitine — discuss dosage with veterinarian")
        if overlay.skin_support:
            supplements.append("Omega-3 fish oil (EPA+DHA: 50-75mg/kg/day)")
        if is_puppy:
            supplements.append("DHA-enriched puppy food recommended for brain development")
        return supplements

    def _build_schedule(self, daily_calories: int, meals_per_day: int) -> list[dict]:
        schedule_templates = {
            2: [("Breakfast", "7:00 AM", 0.5), ("Dinner", "6:00 PM", 0.5)],
            3: [("Breakfast", "7:00 AM", 0.34), ("Lunch", "12:00 PM", 0.33), ("Dinner", "6:00 PM", 0.33)],
            4: [("Morning", "7:00 AM", 0.25), ("Midday", "11:00 AM", 0.25), ("Afternoon", "3:00 PM", 0.25), ("Evening", "7:00 PM", 0.25)],
        }
        template = schedule_templates.get(meals_per_day, schedule_templates[2])
        return [
            {
                "meal_name": name,
                "time_suggestion": time,
                "amount_kcal": int(daily_calories * fraction),
                "amount_g": int(daily_calories * fraction / 3.5),  # Approx grams
            }
            for name, time, fraction in template
        ]

    def _build_notes(self, overlay: BreedOverlay, is_puppy: bool, health_conditions: list[str]) -> str:
        notes_parts = []
        if is_puppy:
            notes_parts.append("Puppy nutritional requirements are higher per kg body weight. Transition to adult food at 12 months (or 18-24 months for giant breeds).")
        if overlay.bloat_risk:
            notes_parts.append("HIGH BLOAT RISK BREED: Never feed one large meal. Split into 3+ smaller meals. Avoid exercise 1 hour before and after eating. Avoid elevated feeding bowls.")
        if overlay.brachycephalic:
            notes_parts.append("Brachycephalic breed: Use a puzzle feeder or slow-feeder bowl to prevent gulping air. Choose smaller kibble sizes.")
        if overlay.obesity_prone:
            notes_parts.append("Obesity-prone breed: Measure food precisely — do not free-feed. Weigh food with a kitchen scale. Monitor body condition score monthly.")
        if health_conditions:
            notes_parts.append("⚠️ Active health conditions detected. These recommendations are general guidelines. Consult your veterinarian for a medically-tailored diet plan.")
        notes_parts.append("Ensure fresh water is available at all times. Transition to any new diet gradually over 7-10 days to avoid GI upset.")
        return " ".join(notes_parts)


# Module-level singleton for import convenience
diet_engine = DietEngine()
