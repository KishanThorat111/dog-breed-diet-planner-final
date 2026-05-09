"""Tests for the diet recommendation engine."""
from __future__ import annotations

import pytest
from app.services.diet_engine import DietEngine, ENGINE_VERSION


@pytest.fixture
def engine() -> DietEngine:
    return DietEngine()


class TestRERCalculation:
    def test_rer_10kg_dog(self, engine: DietEngine) -> None:
        result = engine.generate(
            breed="labrador_retriever",
            age_months=24,
            weight_kg=10.0,
            activity_level="moderate",
        )
        # RER = 70 �— 10^0.75 ≈ 393.6, multiplier ~1.44 → DER ~567 (with 0.9 obesity modifier)
        assert 400 <= result.daily_calories <= 700

    def test_rer_30kg_dog(self, engine: DietEngine) -> None:
        result = engine.generate(
            breed="german_shepherd",
            age_months=36,
            weight_kg=30.0,
            activity_level="active",
        )
        # RER = 70 �— 30^0.75 ≈ 1014, multiplier ~2.0 → DER ~2028
        assert 1500 <= result.daily_calories <= 2500

    def test_puppy_higher_calories(self, engine: DietEngine) -> None:
        puppy_result = engine.generate(
            breed="golden_retriever", age_months=3, weight_kg=5.0, activity_level="moderate"
        )
        adult_result = engine.generate(
            breed="golden_retriever", age_months=36, weight_kg=5.0, activity_level="moderate"
        )
        assert puppy_result.daily_calories > adult_result.daily_calories

    def test_senior_lower_calories(self, engine: DietEngine) -> None:
        adult_result = engine.generate(
            breed="labrador_retriever", age_months=36, weight_kg=25.0, activity_level="light"
        )
        senior_result = engine.generate(
            breed="labrador_retriever", age_months=96, weight_kg=25.0, activity_level="light"
        )
        assert senior_result.daily_calories <= adult_result.daily_calories


class TestBreedOverlays:
    def test_bloat_risk_breed_3_meals(self, engine: DietEngine) -> None:
        result = engine.generate(
            breed="great_dane", age_months=24, weight_kg=60.0, activity_level="moderate"
        )
        assert result.meals_per_day >= 3

    def test_obesity_prone_caloric_reduction(self, engine: DietEngine) -> None:
        labrador = engine.generate(
            breed="labrador_retriever", age_months=24, weight_kg=25.0, activity_level="moderate"
        )
        husky = engine.generate(
            breed="siberian_husky", age_months=24, weight_kg=25.0, activity_level="moderate"
        )
        # Labrador is obesity_prone → should have fewer calories than non-obese-prone breed
        assert labrador.daily_calories < husky.daily_calories

    def test_joint_support_supplements(self, engine: DietEngine) -> None:
        result = engine.generate(
            breed="german_shepherd", age_months=60, weight_kg=30.0, activity_level="moderate"
        )
        assert any("glucosamine" in s.lower() for s in result.supplement_flags)

    def test_dalmatian_low_purine_avoidance(self, engine: DietEngine) -> None:
        result = engine.generate(
            breed="dalmatian", age_months=24, weight_kg=25.0, activity_level="moderate"
        )
        assert any("organ" in food.lower() for food in result.foods_to_avoid)


class TestAllergyExclusions:
    def test_chicken_allergy_excludes_chicken(self, engine: DietEngine) -> None:
        result = engine.generate(
            breed="golden_retriever",
            age_months=24,
            weight_kg=30.0,
            activity_level="moderate",
            allergies=["chicken"],
        )
        for food in result.food_recommendations:
            assert "chicken" not in food["name"].lower()

    def test_grain_allergy_excludes_grains(self, engine: DietEngine) -> None:
        result = engine.generate(
            breed="beagle",
            age_months=24,
            weight_kg=10.0,
            activity_level="moderate",
            allergies=["grain"],
        )
        for food in result.food_recommendations:
            # Brown rice and oatmeal should not appear
            assert "rice" not in food["name"].lower() or "wild" in food["name"].lower()


class TestFeedingSchedule:
    def test_schedule_calories_sum(self, engine: DietEngine) -> None:
        result = engine.generate(
            breed="golden_retriever", age_months=24, weight_kg=30.0, activity_level="moderate"
        )
        total = sum(m["amount_kcal"] for m in result.feeding_schedule)
        # Allow ±5% rounding tolerance
        assert abs(total - result.daily_calories) <= result.daily_calories * 0.05

    def test_engine_version_set(self, engine: DietEngine) -> None:
        result = engine.generate(
            breed="pug", age_months=24, weight_kg=8.0, activity_level="light"
        )
        assert result.engine_version == ENGINE_VERSION
