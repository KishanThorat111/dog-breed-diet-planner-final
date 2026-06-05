"use client";

import { useDietPlans } from "@/hooks/use-diet-plans";
import { useGenerateDietPlan } from "@/hooks/use-diet-plans";
import { usePets } from "@/hooks/use-pets";
import { DietPlanCard } from "@/components/diet/diet-plan-card";
import { ACTIVITY_LEVELS } from "@/lib/constants";
import { Loader2, Sparkles } from "lucide-react";
import { useState } from "react";
import type { GenerateDietPlanRequest } from "@/types";

function toBreedKey(input: string): string {
  return input
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

export default function DietPlansPage() {
  const { dietPlans, isLoading } = useDietPlans();
  const { pets } = usePets();
  const { mutate: generatePlan, isPending: generating } = useGenerateDietPlan();

  const [selectedPetId, setSelectedPetId] = useState("");
  const [breed, setBreed] = useState("");
  const [ageMonths, setAgeMonths] = useState("");
  const [weightKg, setWeightKg] = useState("");
  const [activityLevel, setActivityLevel] = useState("");

  const handleGenerateFromDetails = () => {
    const request: GenerateDietPlanRequest = {};

    if (selectedPetId) {
      request.pet_id = selectedPetId;
    }

    if (breed.trim()) {
      request.breed = toBreedKey(breed);
      request.pet_name = breed.trim();
    }

    if (ageMonths.trim()) {
      request.age_months = Number(ageMonths);
    }

    if (weightKg.trim()) {
      request.weight_kg = Number(weightKg);
    }

    if (activityLevel) {
      request.activity_level = activityLevel;
    }

    generatePlan(request);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Diet Plans</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Personalized, science-backed diet plans for your dogs.
        </p>
      </div>

      <div className="rounded-2xl border border-border bg-card p-5 space-y-4">
        <div>
          <h2 className="font-semibold text-foreground">Generate Diet Plan</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            You can select an existing pet or generate from optional details. Missing values use safe defaults.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <label className="space-y-1.5">
            <span className="text-sm font-medium text-foreground">Existing Pet (optional)</span>
            <select
              value={selectedPetId}
              onChange={(e) => setSelectedPetId(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
            >
              <option value="">Create from details / auto-create pet</option>
              {(pets ?? []).map((pet) => (
                <option key={pet.id} value={pet.id}>
                  {pet.name}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-1.5">
            <span className="text-sm font-medium text-foreground">Breed (optional)</span>
            <input
              value={breed}
              onChange={(e) => setBreed(e.target.value)}
              placeholder="e.g. Labrador Retriever"
              className="w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
          </label>

          <label className="space-y-1.5">
            <span className="text-sm font-medium text-foreground">Age (months, optional)</span>
            <input
              type="number"
              min={0}
              max={360}
              value={ageMonths}
              onChange={(e) => setAgeMonths(e.target.value)}
              placeholder="e.g. 24"
              className="w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
          </label>

          <label className="space-y-1.5">
            <span className="text-sm font-medium text-foreground">Weight (kg, optional)</span>
            <input
              type="number"
              min={0.1}
              max={200}
              step={0.1}
              value={weightKg}
              onChange={(e) => setWeightKg(e.target.value)}
              placeholder="e.g. 18.5"
              className="w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
          </label>

          <label className="space-y-1.5 sm:col-span-2">
            <span className="text-sm font-medium text-foreground">Activity Level (optional)</span>
            <select
              value={activityLevel}
              onChange={(e) => setActivityLevel(e.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
            >
              <option value="">Use default activity level</option>
              {ACTIVITY_LEVELS.map((level) => (
                <option key={level.value} value={level.value}>
                  {level.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <button
          type="button"
          onClick={handleGenerateFromDetails}
          disabled={generating}
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-all hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          Generate Diet Plan
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : dietPlans && dietPlans.length > 0 ? (
        <div className="grid gap-6 lg:grid-cols-2">
          {dietPlans.map((plan) => (
            <DietPlanCard key={plan.id} plan={plan} />
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-border bg-muted/20 py-16 text-center">
          <p className="text-muted-foreground">No diet plans yet.</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Analyze a dog photo to generate your first diet plan.
          </p>
        </div>
      )}
    </div>
  );
}
