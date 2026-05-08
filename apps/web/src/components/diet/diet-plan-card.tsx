"use client";

import type { DietPlan } from "@/types";
import { NutritionChart } from "./nutrition-chart";
import { formatCalories } from "@/lib/utils";
import { CheckCircle2, Flame, Info, Pill, X } from "lucide-react";

interface DietPlanCardProps {
  plan: DietPlan;
}

export function DietPlanCard({ plan }: DietPlanCardProps) {
  return (
    <div className="rounded-2xl border border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="border-b border-border bg-primary/5 p-5">
        <div className="flex items-center gap-2">
          <Flame className="h-5 w-5 text-primary" />
          <h3 className="font-semibold text-foreground">
            {formatCalories(plan.daily_calories)} / day
          </h3>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          Engine: {plan.engine_version} · {new Date(plan.created_at).toLocaleDateString()}
        </p>
      </div>

      <div className="p-5 space-y-5">
        {/* Macros chart */}
        <NutritionChart protein={plan.protein_g} fat={plan.fat_g} carbs={plan.carbs_g} />

        {/* Macros table */}
        <div className="grid grid-cols-3 gap-2 text-center text-sm">
          {[
            { label: "Protein", value: `${Math.round(plan.protein_g)}g`, color: "text-blue-500" },
            { label: "Fat", value: `${Math.round(plan.fat_g)}g`, color: "text-amber-500" },
            { label: "Carbs", value: `${Math.round(plan.carbs_g)}g`, color: "text-emerald-500" },
          ].map((m) => (
            <div key={m.label} className="rounded-lg bg-muted/30 py-2">
              <p className={`font-bold ${m.color}`}>{m.value}</p>
              <p className="text-xs text-muted-foreground">{m.label}</p>
            </div>
          ))}
        </div>

        {/* Food recommendations */}
        {plan.food_recommendations.length > 0 && (
          <div>
            <p className="mb-2 text-sm font-medium text-foreground flex items-center gap-1.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              Recommended Foods
            </p>
            <ul className="space-y-1">
              {plan.food_recommendations.slice(0, 5).map((food, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />
                  <span>
                    <span className="text-foreground font-medium">{food.name}</span>
                    {food.serving_size && ` — ${food.serving_size}`}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Foods to avoid */}
        {plan.foods_to_avoid.length > 0 && (
          <div>
            <p className="mb-2 text-sm font-medium text-foreground flex items-center gap-1.5">
              <X className="h-4 w-4 text-destructive" />
              Foods to Avoid
            </p>
            <div className="flex flex-wrap gap-1.5">
              {plan.foods_to_avoid.map((food, i) => (
                <span key={i} className="rounded-full bg-destructive/10 px-2.5 py-0.5 text-xs text-destructive">
                  {food}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Supplements */}
        {plan.supplement_flags.length > 0 && (
          <div>
            <p className="mb-2 text-sm font-medium text-foreground flex items-center gap-1.5">
              <Pill className="h-4 w-4 text-amber-500" />
              Recommended Supplements
            </p>
            <div className="flex flex-wrap gap-1.5">
              {plan.supplement_flags.map((s, i) => (
                <span key={i} className="rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs text-amber-600 dark:text-amber-400">
                  {s.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Special notes */}
        {plan.special_notes.length > 0 && (
          <div className="rounded-xl border border-border bg-muted/20 p-3">
            <div className="flex items-center gap-1.5 mb-1.5">
              <Info className="h-4 w-4 text-muted-foreground" />
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Notes</p>
            </div>
            {plan.special_notes.map((note, i) => (
              <p key={i} className="text-xs text-muted-foreground">{note}</p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
