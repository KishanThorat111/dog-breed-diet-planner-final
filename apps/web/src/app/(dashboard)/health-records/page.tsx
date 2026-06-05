"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { usePets } from "@/hooks/use-pets";
import {
  useCreateHealthRecord,
  useCreateMedication,
  useDeleteHealthRecord,
  useDeleteMedication,
  useHealthRecords,
  useHealthReminders,
  useHealthSummary,
  useMedications,
  useUpdateMedication,
} from "@/hooks/use-health-records";
import { CalendarClock, ClipboardPlus, Loader2, Pill, Trash2 } from "lucide-react";
import type { HealthRecordType } from "@/types";

const todayIso = new Date().toISOString().slice(0, 10);
const recordTypes: HealthRecordType[] = ["diagnosis", "vet_note", "visit", "lab_result", "symptom", "other"];

const reminderTone: Record<string, string> = {
  overdue: "bg-rose-500/10 text-rose-600",
  due_soon: "bg-amber-500/10 text-amber-600",
};

function formatDate(value: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleDateString();
}

export default function HealthRecordsPage() {
  const { pets, isLoading: petsLoading } = usePets();
  const { summary, isLoading: summaryLoading } = useHealthSummary();
  const { reminders, isLoading: remindersLoading } = useHealthReminders();

  const [selectedPetId, setSelectedPetId] = useState<string | undefined>(undefined);
  const [recordPage, setRecordPage] = useState(1);
  const [medPage, setMedPage] = useState(1);

  const [recordForm, setRecordForm] = useState({
    record_type: "diagnosis" as HealthRecordType,
    title: "",
    details: "",
    recorded_on: todayIso,
    next_visit_on: "",
  });
  const [medForm, setMedForm] = useState({
    medication_name: "",
    dosage: "",
    frequency: "once_daily",
    starts_on: todayIso,
    next_due_on: todayIso,
    notes: "",
  });

  useEffect(() => {
    if (!selectedPetId && pets?.length) {
      setSelectedPetId(pets[0].id);
    }
  }, [pets, selectedPetId]);

  const { data: recordsData, isLoading: recordsLoading } = useHealthRecords(selectedPetId, recordPage, 5);
  const { data: medicationsData, isLoading: medicationsLoading } = useMedications(selectedPetId, medPage, 5);

  const createRecord = useCreateHealthRecord(selectedPetId);
  const deleteRecord = useDeleteHealthRecord(selectedPetId);
  const createMedication = useCreateMedication(selectedPetId);
  const updateMedication = useUpdateMedication(selectedPetId);
  const deleteMedication = useDeleteMedication(selectedPetId);

  const selectedPetName = useMemo(
    () => pets?.find((pet) => pet.id === selectedPetId)?.name ?? "",
    [pets, selectedPetId]
  );

  const onSwitchPet = (petId: string) => {
    setSelectedPetId(petId);
    setRecordPage(1);
    setMedPage(1);
  };

  const handleRecordSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!recordForm.title.trim() || !recordForm.details.trim()) return;

    createRecord.mutate(
      {
        record_type: recordForm.record_type,
        title: recordForm.title.trim(),
        details: recordForm.details.trim(),
        recorded_on: recordForm.recorded_on,
        next_visit_on: recordForm.next_visit_on || undefined,
      },
      {
        onSuccess: () => {
          setRecordForm((prev) => ({ ...prev, title: "", details: "", next_visit_on: "" }));
        },
      }
    );
  };

  const handleMedicationSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!medForm.medication_name.trim() || !medForm.dosage.trim()) return;

    createMedication.mutate(
      {
        medication_name: medForm.medication_name.trim(),
        dosage: medForm.dosage.trim(),
        frequency: medForm.frequency.trim(),
        starts_on: medForm.starts_on,
        next_due_on: medForm.next_due_on || undefined,
        notes: medForm.notes || undefined,
      },
      {
        onSuccess: () => {
          setMedForm((prev) => ({ ...prev, medication_name: "", dosage: "", notes: "" }));
        },
      }
    );
  };

  return (
    <div className="space-y-7 pb-20 lg:pb-0">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground sm:text-3xl">Health Records</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage diagnoses, vet notes, visits, and medication schedules for every pet.
          </p>
        </div>

        <div className="min-w-[220px]">
          <label htmlFor="pet" className="mb-1 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Active Pet
          </label>
          <select
            id="pet"
            value={selectedPetId ?? ""}
            onChange={(event) => onSwitchPet(event.target.value)}
            disabled={petsLoading || !pets?.length}
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground"
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
          { label: "Health Records", value: summary?.total_records ?? 0 },
          { label: "Active Medications", value: summary?.active_medications ?? 0 },
          { label: "Due in 7 Days", value: summary?.due_medications_7d ?? 0 },
          { label: "Visits in 30 Days", value: summary?.upcoming_visits_30d ?? 0 },
        ].map((card) => (
          <article key={card.label} className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">{card.label}</p>
            <p className="mt-3 text-2xl font-bold text-foreground">
              {summaryLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : card.value}
            </p>
          </article>
        ))}
      </div>

      <section className="rounded-xl border border-border bg-card p-5">
        <div className="flex items-center gap-2">
          <CalendarClock className="h-4 w-4 text-amber-600" />
          <h2 className="text-base font-semibold text-foreground">Reminder Center</h2>
        </div>

        <div className="mt-3 space-y-2">
          {remindersLoading ? (
            <p className="text-sm text-muted-foreground">Loading reminders...</p>
          ) : reminders?.length ? (
            reminders.slice(0, 8).map((item) => (
              <article key={`${item.reminder_type}-${item.item_id}`} className="rounded-lg border border-border/70 p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-foreground">
                    {item.pet_name}: {item.title}
                  </p>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${reminderTone[item.status] || "bg-muted text-muted-foreground"}`}>
                    {item.status.replace("_", " ")}
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {item.reminder_type.replace("_", " ")} · Due {formatDate(item.due_on)} ({item.days_until_due} days)
                </p>
              </article>
            ))
          ) : (
            <p className="text-sm text-muted-foreground">No reminders found.</p>
          )}
        </div>
      </section>

      <div className="grid gap-5 xl:grid-cols-2">
        <section className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center gap-2">
            <ClipboardPlus className="h-4 w-4 text-sky-600" />
            <h2 className="text-base font-semibold text-foreground">{selectedPetName || "Pet"} Records</h2>
          </div>

          <form onSubmit={handleRecordSubmit} className="mt-4 grid gap-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-sm text-foreground">
                Record Type
                <select
                  value={recordForm.record_type}
                  onChange={(event) =>
                    setRecordForm((prev) => ({ ...prev, record_type: event.target.value as HealthRecordType }))
                  }
                  className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                >
                  {recordTypes.map((type) => (
                    <option key={type} value={type}>
                      {type.replace("_", " ")}
                    </option>
                  ))}
                </select>
              </label>

              <label className="text-sm text-foreground">
                Recorded On
                <input
                  type="date"
                  value={recordForm.recorded_on}
                  onChange={(event) => setRecordForm((prev) => ({ ...prev, recorded_on: event.target.value }))}
                  className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                />
              </label>
            </div>

            <label className="text-sm text-foreground">
              Title
              <input
                type="text"
                value={recordForm.title}
                onChange={(event) => setRecordForm((prev) => ({ ...prev, title: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                placeholder="Annual vet visit"
                required
              />
            </label>

            <label className="text-sm text-foreground">
              Details
              <textarea
                value={recordForm.details}
                onChange={(event) => setRecordForm((prev) => ({ ...prev, details: event.target.value }))}
                className="mt-1 h-24 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                placeholder="Clinical notes, diagnosis, observations..."
                required
              />
            </label>

            <label className="text-sm text-foreground">
              Next Visit Date (optional)
              <input
                type="date"
                value={recordForm.next_visit_on}
                onChange={(event) => setRecordForm((prev) => ({ ...prev, next_visit_on: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              />
            </label>

            <button
              type="submit"
              disabled={!selectedPetId || createRecord.isPending}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-sky-600 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-60"
            >
              {createRecord.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Save Record
            </button>
          </form>

          <div className="mt-4 space-y-2">
            {recordsLoading ? (
              <p className="text-sm text-muted-foreground">Loading records...</p>
            ) : recordsData?.items?.length ? (
              recordsData.items.map((record) => (
                <article key={record.id} className="rounded-lg border border-border/70 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-foreground">{record.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {record.record_type.replace("_", " ")} · {formatDate(record.recorded_on)}
                        {record.next_visit_on ? ` · Next visit ${formatDate(record.next_visit_on)}` : ""}
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">{record.details}</p>
                    </div>
                    <button
                      onClick={() => deleteRecord.mutate(record.id)}
                      className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground"
                      title="Delete record"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </article>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No health records yet for this pet.</p>
            )}
          </div>

          {recordsData && recordsData.pages > 1 ? (
            <div className="mt-4 flex items-center justify-end gap-2">
              <button
                onClick={() => setRecordPage((prev) => Math.max(1, prev - 1))}
                disabled={recordPage <= 1}
                className="rounded-md border border-border px-3 py-1.5 text-xs disabled:opacity-40"
              >
                Prev
              </button>
              <span className="text-xs text-muted-foreground">
                Page {recordsData.page} of {recordsData.pages}
              </span>
              <button
                onClick={() => setRecordPage((prev) => Math.min(recordsData.pages, prev + 1))}
                disabled={recordPage >= recordsData.pages}
                className="rounded-md border border-border px-3 py-1.5 text-xs disabled:opacity-40"
              >
                Next
              </button>
            </div>
          ) : null}
        </section>

        <section className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center gap-2">
            <Pill className="h-4 w-4 text-emerald-600" />
            <h2 className="text-base font-semibold text-foreground">Medication Schedule</h2>
          </div>

          <form onSubmit={handleMedicationSubmit} className="mt-4 grid gap-3 sm:grid-cols-2">
            <label className="sm:col-span-2 text-sm text-foreground">
              Medication Name
              <input
                type="text"
                value={medForm.medication_name}
                onChange={(event) => setMedForm((prev) => ({ ...prev, medication_name: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                placeholder="Amoxicillin"
                required
              />
            </label>

            <label className="text-sm text-foreground">
              Dosage
              <input
                type="text"
                value={medForm.dosage}
                onChange={(event) => setMedForm((prev) => ({ ...prev, dosage: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                placeholder="250mg"
                required
              />
            </label>

            <label className="text-sm text-foreground">
              Frequency
              <input
                type="text"
                value={medForm.frequency}
                onChange={(event) => setMedForm((prev) => ({ ...prev, frequency: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                placeholder="twice_daily"
                required
              />
            </label>

            <label className="text-sm text-foreground">
              Start Date
              <input
                type="date"
                value={medForm.starts_on}
                onChange={(event) => setMedForm((prev) => ({ ...prev, starts_on: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              />
            </label>

            <label className="text-sm text-foreground">
              Next Due
              <input
                type="date"
                value={medForm.next_due_on}
                onChange={(event) => setMedForm((prev) => ({ ...prev, next_due_on: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              />
            </label>

            <label className="sm:col-span-2 text-sm text-foreground">
              Notes
              <input
                type="text"
                value={medForm.notes}
                onChange={(event) => setMedForm((prev) => ({ ...prev, notes: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                placeholder="After breakfast"
              />
            </label>

            <button
              type="submit"
              disabled={!selectedPetId || createMedication.isPending}
              className="sm:col-span-2 inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-60"
            >
              {createMedication.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Add Medication
            </button>
          </form>

          <div className="mt-4 space-y-2">
            {medicationsLoading ? (
              <p className="text-sm text-muted-foreground">Loading medication schedules...</p>
            ) : medicationsData?.items?.length ? (
              medicationsData.items.map((med) => (
                <article key={med.id} className="rounded-lg border border-border/70 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-foreground">
                        {med.medication_name} · {med.dosage}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {med.frequency} · Next due {formatDate(med.next_due_on)}
                      </p>
                    </div>
                    <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${med.is_active ? "bg-emerald-500/10 text-emerald-600" : "bg-muted text-muted-foreground"}`}>
                      {med.is_active ? "active" : "inactive"}
                    </span>
                  </div>

                  <div className="mt-3 flex items-center justify-end gap-2">
                    <button
                      onClick={() => updateMedication.mutate({ id: med.id, payload: { is_active: !med.is_active } })}
                      className="rounded-md border border-border px-2.5 py-1.5 text-xs"
                    >
                      {med.is_active ? "Mark Inactive" : "Mark Active"}
                    </button>
                    <button
                      onClick={() => deleteMedication.mutate(med.id)}
                      className="rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                    >
                      Delete
                    </button>
                  </div>
                </article>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No medication schedules yet for this pet.</p>
            )}
          </div>

          {medicationsData && medicationsData.pages > 1 ? (
            <div className="mt-4 flex items-center justify-end gap-2">
              <button
                onClick={() => setMedPage((prev) => Math.max(1, prev - 1))}
                disabled={medPage <= 1}
                className="rounded-md border border-border px-3 py-1.5 text-xs disabled:opacity-40"
              >
                Prev
              </button>
              <span className="text-xs text-muted-foreground">
                Page {medicationsData.page} of {medicationsData.pages}
              </span>
              <button
                onClick={() => setMedPage((prev) => Math.min(medicationsData.pages, prev + 1))}
                disabled={medPage >= medicationsData.pages}
                className="rounded-md border border-border px-3 py-1.5 text-xs disabled:opacity-40"
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
