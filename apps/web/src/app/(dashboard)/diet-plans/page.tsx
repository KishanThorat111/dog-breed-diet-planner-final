"use client";

import { useDietPlans } from "@/hooks/use-diet-plans";
import { DietPlanCard } from "@/components/diet/diet-plan-card";
import { Loader2 } from "lucide-react";

export default function DietPlansPage() {
  const { dietPlans, isLoading } = useDietPlans();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Diet Plans</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Personalized, science-backed diet plans for your dogs.
        </p>
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
