"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useApiClient } from "@/lib/api-client";
import { toast } from "sonner";

interface TopupResult {
  ok: boolean;
  credits: number;
}

export default function AdminCreditsPage() {
  const api = useApiClient();
  const [userId, setUserId] = useState("");
  const [credits, setCredits] = useState(100);

  const mutation = useMutation<TopupResult, Error, { user_id: string; credits: number }>({
    mutationFn: async (payload) => {
      const res = await api.post("/admin/credits/topup", payload);
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(`Credits updated: ${data.credits}`);
    },
    onError: (err) => {
      toast.error(err.message || "Top-up failed");
    },
  });

  return (
    <div className="space-y-6 max-w-xl">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Credit Operations</h1>
        <p className="mt-1 text-sm text-muted-foreground">Admin utility for trial/plan credit corrections.</p>
      </div>

      <div className="rounded-xl border border-border bg-card p-4 space-y-4">
        <label className="block text-sm text-foreground">
          User ID
          <input
            value={userId}
            onChange={(event) => setUserId(event.target.value)}
            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
            placeholder="00000000-0000-0000-0000-000000000000"
          />
        </label>

        <label className="block text-sm text-foreground">
          Credits to Add
          <input
            type="number"
            min={1}
            value={credits}
            onChange={(event) => setCredits(Number(event.target.value || 0))}
            className="mt-1 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
          />
        </label>

        <button
          onClick={() => mutation.mutate({ user_id: userId.trim(), credits })}
          disabled={!userId.trim() || credits <= 0 || mutation.isPending}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
        >
          {mutation.isPending ? "Applying..." : "Apply Top-up"}
        </button>

        {mutation.data ? (
          <p className="text-sm text-emerald-600">Operation succeeded. New balance: {mutation.data.credits}</p>
        ) : null}
      </div>
    </div>
  );
}
