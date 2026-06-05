"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "@/lib/api-client";

interface UsageRow {
  id: string;
  user_id: string | null;
  provider: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  caller: string | null;
  created_at: string | null;
}

interface UsageResponse {
  items: UsageRow[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export default function AdminAIUsagePage() {
  const api = useApiClient();
  const [page, setPage] = useState(1);
  const pageSize = 25;

  const { data, isLoading } = useQuery<UsageResponse>({
    queryKey: ["admin-ai-usage", page, pageSize],
    queryFn: async () => {
      const res = await api.get(`/admin/ai/usage?page=${page}&page_size=${pageSize}`);
      return res.data;
    },
  });

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading AI usage...</p>;
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-foreground">AI Usage</h1>
        <p className="mt-1 text-sm text-muted-foreground">Provider/model token telemetry for admin auditing.</p>
      </div>

      <div className="overflow-x-auto rounded-xl border border-border">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-3 py-2">User</th>
              <th className="px-3 py-2">Provider</th>
              <th className="px-3 py-2">Model</th>
              <th className="px-3 py-2">Prompt</th>
              <th className="px-3 py-2">Completion</th>
              <th className="px-3 py-2">Caller</th>
              <th className="px-3 py-2">Created</th>
            </tr>
          </thead>
          <tbody>
            {data?.items?.length ? (
              data.items.map((row) => (
                <tr key={row.id} className="border-t border-border/70">
                  <td className="px-3 py-2 text-muted-foreground">{row.user_id ?? "anon"}</td>
                  <td className="px-3 py-2">{row.provider}</td>
                  <td className="px-3 py-2">{row.model}</td>
                  <td className="px-3 py-2">{row.prompt_tokens}</td>
                  <td className="px-3 py-2">{row.completion_tokens}</td>
                  <td className="px-3 py-2">{row.caller ?? "-"}</td>
                  <td className="px-3 py-2 text-muted-foreground">
                    {row.created_at ? new Date(row.created_at).toLocaleString() : "-"}
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td className="px-3 py-6 text-center text-muted-foreground" colSpan={7}>
                  No AI usage events found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => setPage((prev) => Math.max(1, prev - 1))}
          disabled={page <= 1}
          className="rounded border border-border px-3 py-1.5 text-sm disabled:opacity-40"
        >
          Prev
        </button>
        <span className="text-sm text-muted-foreground">
          Page {data?.page ?? 1} of {data?.pages ?? 1}
        </span>
        <button
          onClick={() => setPage((prev) => Math.min(data?.pages ?? 1, prev + 1))}
          disabled={page >= (data?.pages ?? 1)}
          className="rounded border border-border px-3 py-1.5 text-sm disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  );
}
