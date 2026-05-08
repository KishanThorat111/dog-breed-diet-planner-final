"use client";

import { usePet } from "@/hooks/use-pets";
import { useDietPlans } from "@/hooks/use-diet-plans";
import { useGenerateDietPlan } from "@/hooks/use-diet-plans";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Loader2, Sparkles } from "lucide-react";
import { formatAge, formatWeight, capitalize } from "@/lib/utils";
import { DietPlanCard } from "@/components/diet/diet-plan-card";

export default function PetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: pet, isLoading } = usePet(id);
  const { dietPlans, isLoading: plansLoading } = useDietPlans(id);
  const { mutate: generatePlan, isPending: generating } = useGenerateDietPlan();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (!pet) {
    return (
      <div className="py-20 text-center text-muted-foreground">Pet not found.</div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <Link
          href="/pets"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to pets
        </Link>
        <h1 className="mt-3 text-2xl font-bold text-foreground">{pet.name}</h1>
        {pet.breed && (
          <p className="mt-1 text-muted-foreground capitalize">{pet.breed.replace(/_/g, " ")}</p>
        )}
      </div>

      {/* Profile */}
      <div className="rounded-2xl border border-border bg-card p-5 space-y-3">
        <h2 className="font-semibold text-foreground">Profile</h2>
        <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
          {[
            { label: "Age", value: formatAge(pet.age_months) },
            { label: "Weight", value: formatWeight(pet.weight_kg) },
            { label: "Life Stage", value: capitalize(pet.life_stage) },
            { label: "Activity", value: capitalize(pet.activity_level) },
            { label: "Sex", value: pet.sex ? capitalize(pet.sex) : "Unknown" },
          ].map((field) => (
            <div key={field.label}>
              <p className="text-xs text-muted-foreground">{field.label}</p>
              <p className="font-medium text-foreground">{field.value}</p>
            </div>
          ))}
        </div>
        {pet.allergies.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-1">Allergies</p>
            <div className="flex flex-wrap gap-1.5">
              {pet.allergies.map((a) => (
                <span key={a} className="rounded-full bg-destructive/10 px-2 py-0.5 text-xs text-destructive">
                  {a}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Diet Plans */}
      <div>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-semibold text-foreground">Diet Plans</h2>
          <button
            onClick={() => generatePlan({ pet_id: id })}
            disabled={generating}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-all hover:bg-primary/90 disabled:opacity-60"
          >
            {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            Generate Plan
          </button>
        </div>
        {plansLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : dietPlans && dietPlans.length > 0 ? (
          <div className="space-y-4">
            {dietPlans.map((plan) => <DietPlanCard key={plan.id} plan={plan} />)}
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-border bg-muted/20 py-10 text-center text-sm text-muted-foreground">
            No diet plans yet. Generate one above or analyze a photo.
          </div>
        )}
      </div>
    </div>
  );
}
