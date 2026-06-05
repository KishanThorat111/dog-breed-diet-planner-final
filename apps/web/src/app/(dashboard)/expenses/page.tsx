"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Loader2, Receipt, Trash2 } from "lucide-react";
import { usePets } from "@/hooks/use-pets";
import {
  useCreateExpense,
  useDeleteExpense,
  useExpenses,
  useHealthSummary,
  useUpdateExpense,
} from "@/hooks/use-health-records";
import type { ExpenseCategory } from "@/types";

const todayIso = new Date().toISOString().slice(0, 10);
const categories: ExpenseCategory[] = ["food", "medicine", "vaccine", "vet_visit", "accessory", "other"];

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

function formatDate(value: string) {
  return new Date(value).toLocaleDateString();
}

export default function ExpensesPage() {
  const { pets, isLoading: petsLoading } = usePets();
  const { summary, isLoading: summaryLoading } = useHealthSummary();

  const [selectedPetId, setSelectedPetId] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(1);
  const [editingId, setEditingId] = useState<string | null>(null);

  const [form, setForm] = useState({
    category: "food" as ExpenseCategory,
    amount: "",
    expense_on: todayIso,
    description: "",
    vendor: "",
    notes: "",
  });

  useEffect(() => {
    if (!selectedPetId && pets?.length) {
      setSelectedPetId(pets[0].id);
    }
  }, [pets, selectedPetId]);

  const { data: expensesData, isLoading: expensesLoading } = useExpenses(selectedPetId, page, 10);

  const createExpense = useCreateExpense(selectedPetId);
  const updateExpense = useUpdateExpense(selectedPetId);
  const deleteExpense = useDeleteExpense(selectedPetId);

  const selectedPet = useMemo(() => pets?.find((pet) => pet.id === selectedPetId), [pets, selectedPetId]);

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const amount = Number(form.amount);
    if (!form.description.trim() || Number.isNaN(amount) || amount <= 0) return;

    createExpense.mutate(
      {
        category: form.category,
        amount,
        expense_on: form.expense_on,
        description: form.description.trim(),
        vendor: form.vendor || undefined,
        notes: form.notes || undefined,
      },
      {
        onSuccess: () => {
          setForm((prev) => ({
            ...prev,
            amount: "",
            description: "",
            vendor: "",
            notes: "",
          }));
        },
      }
    );
  };

  const onQuickUpdateCategory = (id: string, category: ExpenseCategory) => {
    setEditingId(id);
    updateExpense.mutate(
      { id, payload: { category } },
      {
        onSettled: () => setEditingId(null),
      }
    );
  };

  return (
    <div className="space-y-7 pb-20 lg:pb-0">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground sm:text-3xl">Expense Tracking</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Log pet costs and monitor monthly spending by category.
          </p>
        </div>

        <div className="min-w-[220px]">
          <label htmlFor="pet" className="mb-1 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Active Pet
          </label>
          <select
            id="pet"
            value={selectedPetId ?? ""}
            onChange={(event) => {
              setSelectedPetId(event.target.value);
              setPage(1);
            }}
            disabled={petsLoading || !pets?.length}
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
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
        <article className="rounded-xl border border-border bg-card p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Monthly Total</p>
          <p className="mt-3 text-2xl font-bold text-foreground">
            {summaryLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : currency.format(summary?.monthly_expense_total ?? 0)}
          </p>
        </article>
        {(summary?.expense_by_category ?? []).slice(0, 3).map((item) => (
          <article key={item.category} className="rounded-xl border border-border bg-card p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">{item.category.replace("_", " ")}</p>
            <p className="mt-3 text-2xl font-bold text-foreground">{currency.format(item.total_amount)}</p>
          </article>
        ))}
      </div>

      <div className="grid gap-5 xl:grid-cols-[380px_1fr]">
        <section className="rounded-xl border border-border bg-card p-5">
          <div className="flex items-center gap-2">
            <Receipt className="h-4 w-4 text-fuchsia-600" />
            <h2 className="text-base font-semibold text-foreground">Add Expense</h2>
          </div>

          <form onSubmit={onSubmit} className="mt-4 grid gap-3">
            <label className="text-sm text-foreground">
              Category
              <select
                value={form.category}
                onChange={(event) => setForm((prev) => ({ ...prev, category: event.target.value as ExpenseCategory }))}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              >
                {categories.map((category) => (
                  <option key={category} value={category}>
                    {category.replace("_", " ")}
                  </option>
                ))}
              </select>
            </label>

            <label className="text-sm text-foreground">
              Amount
              <input
                type="number"
                min="0"
                step="0.01"
                value={form.amount}
                onChange={(event) => setForm((prev) => ({ ...prev, amount: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                placeholder="0.00"
                required
              />
            </label>

            <label className="text-sm text-foreground">
              Date
              <input
                type="date"
                value={form.expense_on}
                onChange={(event) => setForm((prev) => ({ ...prev, expense_on: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
              />
            </label>

            <label className="text-sm text-foreground">
              Description
              <input
                type="text"
                value={form.description}
                onChange={(event) => setForm((prev) => ({ ...prev, description: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                placeholder="Monthly kibble purchase"
                required
              />
            </label>

            <label className="text-sm text-foreground">
              Vendor
              <input
                type="text"
                value={form.vendor}
                onChange={(event) => setForm((prev) => ({ ...prev, vendor: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                placeholder="PetCare Store"
              />
            </label>

            <label className="text-sm text-foreground">
              Notes
              <textarea
                value={form.notes}
                onChange={(event) => setForm((prev) => ({ ...prev, notes: event.target.value }))}
                className="mt-1 h-20 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                placeholder="Paid via card"
              />
            </label>

            <button
              type="submit"
              disabled={!selectedPetId || createExpense.isPending}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-fuchsia-600 px-4 py-2.5 text-sm font-medium text-white disabled:opacity-60"
            >
              {createExpense.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Save Expense
            </button>
          </form>
        </section>

        <section className="rounded-xl border border-border bg-card p-5">
          <h2 className="text-base font-semibold text-foreground">
            {selectedPet?.name ?? "Pet"} Expense History
          </h2>

          <div className="mt-4 space-y-2">
            {expensesLoading ? (
              <p className="text-sm text-muted-foreground">Loading expenses...</p>
            ) : expensesData?.items?.length ? (
              expensesData.items.map((item) => (
                <article key={item.id} className="rounded-lg border border-border/70 p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-foreground">{item.description}</p>
                      <p className="text-xs text-muted-foreground">
                        {item.category.replace("_", " ")} · {formatDate(item.expense_on)}
                        {item.vendor ? ` · ${item.vendor}` : ""}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-foreground">{currency.format(item.amount)}</p>
                      <button
                        onClick={() => deleteExpense.mutate(item.id)}
                        className="mt-1 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Delete
                      </button>
                    </div>
                  </div>

                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    {categories.map((category) => (
                      <button
                        key={category}
                        onClick={() => onQuickUpdateCategory(item.id, category)}
                        disabled={editingId === item.id || item.category === category}
                        className={`rounded-full border px-2.5 py-1 text-xs ${
                          item.category === category
                            ? "border-foreground/20 bg-foreground/5 text-foreground"
                            : "border-border text-muted-foreground hover:text-foreground"
                        } disabled:opacity-60`}
                      >
                        {category.replace("_", " ")}
                      </button>
                    ))}
                  </div>
                </article>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">No expenses logged yet for this pet.</p>
            )}
          </div>

          {expensesData && expensesData.pages > 1 ? (
            <div className="mt-4 flex items-center justify-end gap-2">
              <button
                onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                disabled={page <= 1}
                className="rounded-md border border-border px-3 py-1.5 text-xs disabled:opacity-40"
              >
                Prev
              </button>
              <span className="text-xs text-muted-foreground">
                Page {expensesData.page} of {expensesData.pages}
              </span>
              <button
                onClick={() => setPage((prev) => Math.min(expensesData.pages, prev + 1))}
                disabled={page >= expensesData.pages}
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
