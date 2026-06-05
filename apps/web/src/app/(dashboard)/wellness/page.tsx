"use client";

import { FormEvent, useEffect, useState } from "react";
import { usePets } from "@/hooks/use-pets";
import {
  useCreateVaccination,
  useCreateWeightLog,
  useDeleteVaccination,
  useDeleteWeightLog,
  useUpdateVaccination,
  useVaccinations,
  useWeightLogs,
  useWellnessSummary,
} from "@/hooks/use-wellness";
import { Activity, AlertTriangle, CheckCircle2, Loader2, Syringe, Trash2, Weight } from "lucide-react";

const todayIso = new Date().toISOString().slice(0, 10);

const statusClass: Record<string, string> = {
  overdue: "bg-rose-500/10 text-rose-600",
  due_soon: "bg-amber-500/10 text-amber-600",
  scheduled: "bg-sky-500/10 text-sky-600",
  completed: "bg-emerald-500/10 text-emerald-600",
};

function formatDate(value: string) {
  return new Date(value).toLocaleDateString();
}

export default function WellnessPage() {
  const { pets, isLoading: petsLoading } = usePets();
  const { summary, isLoading: summaryLoading } = useWellnessSummary();

  const [selectedPetId, setSelectedPetId] = useState<string | undefined>(undefined);
  const [weightPage, setWeightPage] = useState(1);
  const [vaccinationPage, setVaccinationPage] = useState(1);

  const [weightForm, setWeightForm] = useState({ measured_on: todayIso, weight_kg: "", notes: "" });
  const [vaccinationForm, setVaccinationForm] = useState({
    vaccine_name: "",
    due_on: todayIso,
    reminder_days_before: "7",
    notes: "",
  });

  useEffect(() => {
    if (!selectedPetId && pets?.length) {
      setSelectedPetId(pets[0].id);
    }
  }, [pets, selectedPetId]);

  const { data: weightData, isLoading: weightsLoading } = useWeightLogs(selectedPetId, weightPage, 5);
  const { data: vaccinationData, isLoading: vaccinationsLoading } = useVaccinations(
    selectedPetId,
    vaccinationPage,
    5
  );

  const createWeight = useCreateWeightLog(selectedPetId);
  const deleteWeight = useDeleteWeightLog(selectedPetId);
  const createVaccination = useCreateVaccination(selectedPetId);
  const updateVaccination = useUpdateVaccination(selectedPetId);
  const deleteVaccination = useDeleteVaccination(selectedPetId);

  const onChangePet = (petId: string) => {
    setSelectedPetId(petId);
    setWeightPage(1);
    setVaccinationPage(1);
  };

  const handleWeightSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const weight = Number(weightForm.weight_kg);
    if (!weight || weight <= 0) {
      return;
    }

    createWeight.mutate(
      {
        measured_on: weightForm.measured_on,
        weight_kg: weight,
        notes: weightForm.notes || undefined,
      },
      {
        onSuccess: () => {
          setWeightForm((prev) => ({ ...prev, weight_kg: "", notes: "" }));
        },
      }
    );
  };

  const handleVaccinationSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!vaccinationForm.vaccine_name.trim()) {
      return;
    }

    createVaccination.mutate(
      {
        vaccine_name: vaccinationForm.vaccine_name.trim(),
        due_on: vaccinationForm.due_on,
        reminder_days_before: Number(vaccinationForm.reminder_days_before || "7"),
        notes: vaccinationForm.notes || undefined,
      },
      {
        onSuccess: () => {
          setVaccinationForm((prev) => ({ ...prev, vaccine_name: "", notes: "" }));
        },
      }
    );
  };

  const markCompleted = (id: string) => {
    updateVaccination.mutate({
      id,
      payload: { is_completed: true, administered_on: todayIso },
    });
  };

  return (
    <div className="space-y-7 pb-20 lg:pb-0">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground sm:text-3xl">Wellness Center</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Track weight trends, vaccine schedules, and upcoming reminders in one place.
          </p>
        </div>

        <div className="min-w-[220px]">
          <label htmlFor="pet" className="mb-1 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Active Pet
          </label>
          <select
            id="pet"
            value={selectedPetId ?? ""}
            onChange={(event) => onChangePet(event.target.value)}
            disabled={petsLoading || !pets?.length}
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none ring-primary/30 transition focus:ring"
          >
            {!pets?.length ? <option value="">Add a pet first</option> : null}
            {pets?.map((pet) => (
              <option key={pet.id} value={pet.id}>
                {pet.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          {
            label: "Total Pets",
            value: summary?.total_pets ?? 0,
            icon: Activity,
            tone: "text-sky-600",
          },
          {
            label: "Weight Logs",
            value: summary?.pets_with_weight_logs ?? 0,
            icon: Weight,
            tone: "text-emerald-600",
          },
          {
            label: "Upcoming Vaccines",
            value: summary?.upcoming_vaccinations ?? 0,
            icon: Syringe,
            tone: "text-amber-600",
          },
          {
            label: "Overdue Vaccines",
            value: summary?.overdue_vaccinations ?? 0,
            icon: AlertTriangle,
            tone: "text-rose-600",
          },
        ].map((card) => (
          <article key={card.label} className="rounded-2xl border border-border bg-card p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase tracking-wide text-muted-foreground">{card.label}</span>
              <card.icon className={`h-4 w-4 ${card.tone}`} />
            </div>
            <p className="mt-3 text-3xl font-bold text-foreground">
              {summaryLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : card.value}
            </p>
          </article>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <section className="rounded-2xl border border-border bg-card p-4">
          <h2 className="text-base font-semibold text-foreground">Weight Trends</h2>
          <div className="mt-3 space-y-2">
            {summary?.pet_trends?.length ? (
              summary.pet_trends.map((trend) => (
                <div key={trend.pet_id} className="flex items-center justify-between rounded-xl border border-border/70 p-3">
                  <div>
                    <p className="text-sm font-medium text-foreground">{trend.pet_name}</p>
                    <p className="text-xs text-muted-foreground">
                      Latest: {trend.latest_weight_kg ?? "-"} kg
                      {trend.delta_kg !== null ? ` · Delta: ${Number(trend.delta_kg).toFixed(1)} kg` : ""}
                    </p>
                  </div>
                  <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-foreground">
                    {trend.trend.replace("_", " ")}
                  </span>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No trend data yet.</p>
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-border bg-card p-4">
          <h2 className="text-base font-semibold text-foreground">Upcoming Reminders</h2>
          <div className="mt-3 space-y-2">
            {summary?.reminders?.length ? (
              summary.reminders.map((reminder) => (
                <div key={reminder.vaccination_id} className="rounded-xl border border-border/70 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-medium text-foreground">
                      {reminder.pet_name}: {reminder.vaccine_name}
                    </p>
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                        statusClass[reminder.status] || "bg-muted text-muted-foreground"
                      }`}
                    >
                      {reminder.status.replace("_", " ")}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Due {formatDate(reminder.due_on)} ({reminder.days_until_due} days)
                  </p>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No reminders in the next 30 days.</p>
            )}
          </div>
        </section>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <section className="rounded-2xl border border-border bg-card p-5">
          <div className="flex items-center gap-2">
            <Weight className="h-4 w-4 text-emerald-600" />
            <h2 className="text-base font-semibold text-foreground">Weight Tracker</h2>
          </div>

          <form onSubmit={handleWeightSubmit} className="mt-4 grid gap-3 sm:grid-cols-2">
            <label className="text-sm text-foreground">
              Measured On
              <input
                type="date"
                value={weightForm.measured_on}
                onChange={(event) => setWeightForm((prev) => ({ ...prev, measured_on: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none ring-primary/30 focus:ring"
                required
              />
            </label>

            <label className="text-sm text-foreground">
              Weight (kg)
              <input
                type="number"
                min="0.1"
                step="0.1"
                value={weightForm.weight_kg}
                onChange={(event) => setWeightForm((prev) => ({ ...prev, weight_kg: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none ring-primary/30 focus:ring"
                placeholder="12.4"
                required
              />
            </label>

            <label className="sm:col-span-2 text-sm text-foreground">
              Notes
              <input
                type="text"
                value={weightForm.notes}
                onChange={(event) => setWeightForm((prev) => ({ ...prev, notes: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none ring-primary/30 focus:ring"
                placeholder="Optional note"
              />
            </label>

            <button
              type="submit"
              disabled={!selectedPetId || createWeight.isPending}
              className="sm:col-span-2 inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-emerald-700 disabled:opacity-60"
            >
              {createWeight.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Add Weight Entry
            </button>
          </form>

          <div className="mt-4 space-y-2">
            {weightsLoading ? (
              <p className="text-sm text-muted-foreground">Loading weight logs...</p>
            ) : weightData?.items?.length ? (
              weightData.items.map((log) => (
                <article key={log.id} className="flex items-center justify-between rounded-xl border border-border/70 p-3">
                  <div>
                    <p className="text-sm font-medium text-foreground">{Number(log.weight_kg).toFixed(1)} kg</p>
                    <p className="text-xs text-muted-foreground">
                      {formatDate(log.measured_on)}{log.notes ? ` · ${log.notes}` : ""}
                    </p>
                  </div>
                  <button
                    onClick={() => deleteWeight.mutate(log.id)}
                    className="rounded-lg p-2 text-muted-foreground transition hover:bg-muted hover:text-foreground"
                    title="Delete weight log"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </article>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No weight entries yet for this pet.</p>
            )}
          </div>

          {weightData && weightData.pages > 1 ? (
            <div className="mt-4 flex items-center justify-end gap-2">
              <button
                onClick={() => setWeightPage((prev) => Math.max(1, prev - 1))}
                disabled={weightPage <= 1}
                className="rounded-md border border-border px-3 py-1.5 text-xs text-foreground disabled:opacity-40"
              >
                Prev
              </button>
              <span className="text-xs text-muted-foreground">
                Page {weightData.page} of {weightData.pages}
              </span>
              <button
                onClick={() => setWeightPage((prev) => Math.min(weightData.pages, prev + 1))}
                disabled={weightPage >= weightData.pages}
                className="rounded-md border border-border px-3 py-1.5 text-xs text-foreground disabled:opacity-40"
              >
                Next
              </button>
            </div>
          ) : null}
        </section>

        <section className="rounded-2xl border border-border bg-card p-5">
          <div className="flex items-center gap-2">
            <Syringe className="h-4 w-4 text-amber-600" />
            <h2 className="text-base font-semibold text-foreground">Vaccination Tracker</h2>
          </div>

          <form onSubmit={handleVaccinationSubmit} className="mt-4 grid gap-3 sm:grid-cols-2">
            <label className="sm:col-span-2 text-sm text-foreground">
              Vaccine Name
              <input
                type="text"
                value={vaccinationForm.vaccine_name}
                onChange={(event) =>
                  setVaccinationForm((prev) => ({ ...prev, vaccine_name: event.target.value }))
                }
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none ring-primary/30 focus:ring"
                placeholder="Rabies"
                required
              />
            </label>

            <label className="text-sm text-foreground">
              Due Date
              <input
                type="date"
                value={vaccinationForm.due_on}
                onChange={(event) => setVaccinationForm((prev) => ({ ...prev, due_on: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none ring-primary/30 focus:ring"
                required
              />
            </label>

            <label className="text-sm text-foreground">
              Reminder (days before)
              <input
                type="number"
                min="0"
                value={vaccinationForm.reminder_days_before}
                onChange={(event) =>
                  setVaccinationForm((prev) => ({ ...prev, reminder_days_before: event.target.value }))
                }
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none ring-primary/30 focus:ring"
              />
            </label>

            <label className="sm:col-span-2 text-sm text-foreground">
              Notes
              <input
                type="text"
                value={vaccinationForm.notes}
                onChange={(event) => setVaccinationForm((prev) => ({ ...prev, notes: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none ring-primary/30 focus:ring"
                placeholder="Optional note"
              />
            </label>

            <button
              type="submit"
              disabled={!selectedPetId || createVaccination.isPending}
              className="sm:col-span-2 inline-flex items-center justify-center gap-2 rounded-lg bg-amber-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-amber-700 disabled:opacity-60"
            >
              {createVaccination.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Add Vaccination
            </button>
          </form>

          <div className="mt-4 space-y-2">
            {vaccinationsLoading ? (
              <p className="text-sm text-muted-foreground">Loading vaccinations...</p>
            ) : vaccinationData?.items?.length ? (
              vaccinationData.items.map((item) => (
                <article key={item.id} className="rounded-xl border border-border/70 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-foreground">{item.vaccine_name}</p>
                      <p className="text-xs text-muted-foreground">
                        Due: {formatDate(item.due_on)}
                        {item.administered_on ? ` · Given: ${formatDate(item.administered_on)}` : ""}
                      </p>
                    </div>
                    <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusClass[item.status]}`}>
                      {item.status.replace("_", " ")}
                    </span>
                  </div>

                  <div className="mt-3 flex items-center justify-end gap-2">
                    {!item.is_completed ? (
                      <button
                        onClick={() => markCompleted(item.id)}
                        className="inline-flex items-center gap-1 rounded-md border border-emerald-500/40 px-2.5 py-1.5 text-xs font-medium text-emerald-600 transition hover:bg-emerald-500/10"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Mark Completed
                      </button>
                    ) : null}
                    <button
                      onClick={() => deleteVaccination.mutate(item.id)}
                      className="rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground transition hover:bg-muted hover:text-foreground"
                    >
                      Delete
                    </button>
                  </div>
                </article>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No vaccinations yet for this pet.</p>
            )}
          </div>

          {vaccinationData && vaccinationData.pages > 1 ? (
            <div className="mt-4 flex items-center justify-end gap-2">
              <button
                onClick={() => setVaccinationPage((prev) => Math.max(1, prev - 1))}
                disabled={vaccinationPage <= 1}
                className="rounded-md border border-border px-3 py-1.5 text-xs text-foreground disabled:opacity-40"
              >
                Prev
              </button>
              <span className="text-xs text-muted-foreground">
                Page {vaccinationData.page} of {vaccinationData.pages}
              </span>
              <button
                onClick={() => setVaccinationPage((prev) => Math.min(vaccinationData.pages, prev + 1))}
                disabled={vaccinationPage >= vaccinationData.pages}
                className="rounded-md border border-border px-3 py-1.5 text-xs text-foreground disabled:opacity-40"
              >
                Next
              </button>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
