"use client";

import type { Prediction } from "@/types";
import { useGenerateDietPlan } from "@/hooks/use-diet-plans";
import { usePets } from "@/hooks/use-pets";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, ChevronRight, Loader2, Sparkles } from "lucide-react";
import { capitalize } from "@/lib/utils";

interface PredictionResultProps {
  prediction: Prediction;
}

export function PredictionResult({ prediction }: PredictionResultProps) {
  const { pets } = usePets();
  const { mutate: generatePlan, isPending } = useGenerateDietPlan();
  const [selectedPetId, setSelectedPetId] = useState<string>("");
  const router = useRouter();

  const topBreed = prediction.all_predictions[0];

  const handleGeneratePlan = () => {
    if (!selectedPetId) return;
    generatePlan(
      { pet_id: selectedPetId, prediction_id: prediction.id },
      { onSuccess: () => router.push("/diet-plans") }
    );
  };

  return (
    <div className="rounded-2xl border border-border bg-card p-5 animate-fade-in">
      <div className="mb-4 flex items-center gap-2">
        <CheckCircle2 className="h-5 w-5 text-emerald-500" />
        <h3 className="font-semibold text-foreground">Breed Identified</h3>
        {prediction.cached && (
          <span className="ml-auto rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
            cached
          </span>
        )}
      </div>

      {/* Top prediction */}
      <div className="mb-4 rounded-xl bg-primary/5 p-4">
        <p className="text-sm text-muted-foreground">Top match</p>
        <p className="mt-1 text-xl font-bold text-foreground">
          {topBreed?.display_name ?? capitalize(prediction.top_breed)}
        </p>
        <div className="mt-2 flex items-center gap-3">
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${Math.round(prediction.top_confidence * 100)}%` }}
            />
          </div>
          <span className="text-sm font-medium text-primary">
            {Math.round(prediction.top_confidence * 100)}%
          </span>
        </div>
        {topBreed?.size && (
          <p className="mt-2 text-xs text-muted-foreground capitalize">
            Size: {topBreed.size}
          </p>
        )}
      </div>

      {/* Top 5 predictions */}
      {prediction.all_predictions.length > 1 && (
        <div className="mb-4 space-y-2">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Other possibilities
          </p>
          {prediction.all_predictions.slice(1, 5).map((p) => (
            <div key={p.breed} className="flex items-center gap-2">
              <span className="flex-1 text-sm text-muted-foreground">
                {p.display_name}
              </span>
              <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-muted-foreground/40"
                  style={{ width: `${Math.round(p.confidence * 100)}%` }}
                />
              </div>
              <span className="w-10 text-right text-xs text-muted-foreground">
                {Math.round(p.confidence * 100)}%
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Generate diet plan */}
      {pets && pets.length > 0 && (
        <div className="border-t border-border pt-4">
          <p className="mb-2 text-sm font-medium text-foreground">Generate diet plan for:</p>
          <div className="flex gap-2">
            <select
              value={selectedPetId}
              onChange={(e) => setSelectedPetId(e.target.value)}
              className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
            >
              <option value="">Select a pet…</option>
              {pets.map((pet) => (
                <option key={pet.id} value={pet.id}>
                  {pet.name}
                </option>
              ))}
            </select>
            <button
              onClick={handleGeneratePlan}
              disabled={!selectedPetId || isPending}
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-all hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  Generate
                  <ChevronRight className="h-3.5 w-3.5" />
                </>
              )}
            </button>
          </div>
        </div>
      )}

      <p className="mt-3 text-xs text-muted-foreground">
        Model: {prediction.model_version} · {prediction.inference_time_ms}ms
      </p>
    </div>
  );
}
