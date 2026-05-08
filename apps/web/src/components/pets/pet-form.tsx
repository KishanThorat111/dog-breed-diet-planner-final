"use client";

import { useCreatePet } from "@/hooks/use-pets";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ACTIVITY_LEVELS, LIFE_STAGES, SEX_OPTIONS } from "@/lib/constants";
import type { PetCreate } from "@/types";
import { Loader2 } from "lucide-react";

export function PetForm() {
  const { mutate: createPet, isPending } = useCreatePet();
  const router = useRouter();

  const [form, setForm] = useState<PetCreate>({
    name: "",
    breed: "",
    age_months: undefined,
    weight_kg: undefined,
    sex: undefined,
    life_stage: "adult",
    activity_level: "moderate",
    allergies: [],
    health_conditions: [],
    is_pregnant: false,
    is_lactating: false,
    notes: "",
  });

  const set = (key: keyof PetCreate, value: unknown) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const payload: PetCreate = { ...form };
    if (!payload.breed) delete payload.breed;
    if (!payload.age_months) delete payload.age_months;
    if (!payload.weight_kg) delete payload.weight_kg;
    if (!payload.sex) delete payload.sex;
    if (!payload.notes) delete payload.notes;
    createPet(payload, { onSuccess: () => router.push("/pets") });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="rounded-2xl border border-border bg-card p-5 space-y-4">
        <h2 className="font-semibold text-foreground">Basic Information</h2>

        <Field label="Name *">
          <input
            required
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
            placeholder="e.g. Buddy"
            className={inputCls}
          />
        </Field>

        <Field label="Breed">
          <input
            value={form.breed || ""}
            onChange={(e) => set("breed", e.target.value)}
            placeholder="e.g. Golden Retriever (or use AI analyze)"
            className={inputCls}
          />
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Age (months)">
            <input
              type="number"
              min={0}
              max={300}
              value={form.age_months ?? ""}
              onChange={(e) => set("age_months", e.target.value ? Number(e.target.value) : undefined)}
              placeholder="e.g. 24"
              className={inputCls}
            />
          </Field>

          <Field label="Weight (kg)">
            <input
              type="number"
              min={0.1}
              max={150}
              step={0.1}
              value={form.weight_kg ?? ""}
              onChange={(e) => set("weight_kg", e.target.value ? Number(e.target.value) : undefined)}
              placeholder="e.g. 25.5"
              className={inputCls}
            />
          </Field>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Sex">
            <select value={form.sex ?? ""} onChange={(e) => set("sex", e.target.value || undefined)} className={inputCls}>
              <option value="">Unknown</option>
              {SEX_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </Field>

          <Field label="Life Stage">
            <select value={form.life_stage} onChange={(e) => set("life_stage", e.target.value)} className={inputCls}>
              {LIFE_STAGES.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </Field>

          <Field label="Activity Level">
            <select value={form.activity_level} onChange={(e) => set("activity_level", e.target.value)} className={inputCls}>
              {ACTIVITY_LEVELS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </Field>
        </div>
      </div>

      <div className="rounded-2xl border border-border bg-card p-5 space-y-4">
        <h2 className="font-semibold text-foreground">Health</h2>
        <Field label="Known Allergies (comma-separated)">
          <input
            value={form.allergies?.join(", ") ?? ""}
            onChange={(e) => set("allergies", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))}
            placeholder="e.g. chicken, wheat"
            className={inputCls}
          />
        </Field>
        <Field label="Health Conditions (comma-separated)">
          <input
            value={form.health_conditions?.join(", ") ?? ""}
            onChange={(e) => set("health_conditions", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))}
            placeholder="e.g. hip dysplasia, obesity"
            className={inputCls}
          />
        </Field>
        <div className="flex gap-6">
          <label className="flex items-center gap-2 text-sm text-foreground">
            <input type="checkbox" checked={form.is_pregnant} onChange={(e) => set("is_pregnant", e.target.checked)} className="rounded" />
            Pregnant
          </label>
          <label className="flex items-center gap-2 text-sm text-foreground">
            <input type="checkbox" checked={form.is_lactating} onChange={(e) => set("is_lactating", e.target.checked)} className="rounded" />
            Lactating
          </label>
        </div>
        <Field label="Notes">
          <textarea
            value={form.notes || ""}
            onChange={(e) => set("notes", e.target.value)}
            rows={3}
            placeholder="Any other information about your dog..."
            className={`${inputCls} resize-none`}
          />
        </Field>
      </div>

      <button
        type="submit"
        disabled={isPending || !form.name}
        className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-3.5 text-sm font-semibold text-primary-foreground shadow-sm transition-all hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Add Pet"}
      </button>
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-foreground">{label}</label>
      {children}
    </div>
  );
}

const inputCls =
  "w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30 transition-shadow";
