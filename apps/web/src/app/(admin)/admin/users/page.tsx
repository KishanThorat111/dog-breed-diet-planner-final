"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useApiClient } from "@/lib/api-client";
import { UserTable } from "@/components/admin/user-table";
import { Users } from "lucide-react";

export default function AdminUsersPage() {
  const api = useApiClient();
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const { data, isLoading } = useQuery({
    queryKey: ["admin-users", page, pageSize],
    queryFn: async () => {
      const res = await api.get(`/admin/users?page=${page}&page_size=${pageSize}`);
      return res.data;
    },
  });

  const totalPages = data?.pages ?? 1;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Users className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-bold text-foreground">Users</h1>
      </div>
      <UserTable users={data?.items ?? []} isLoading={isLoading} />

      <div className="flex items-center gap-2">
        <button
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page <= 1}
          className="rounded border px-3 py-1 text-sm disabled:opacity-50"
        >
          Prev
        </button>
        <span className="text-sm text-muted-foreground">
          Page {page} of {totalPages}
        </span>
        <button
          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          disabled={page >= totalPages}
          className="rounded border px-3 py-1 text-sm disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}
