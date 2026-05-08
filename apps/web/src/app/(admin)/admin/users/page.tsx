"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { UserTable } from "@/components/admin/user-table";
import { Users } from "lucide-react";

export default function AdminUsersPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["admin-users"],
    queryFn: async () => {
      const res = await apiClient.get("/admin/users?limit=100&offset=0");
      return res.data;
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Users className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-bold text-foreground">Users</h1>
      </div>
      <UserTable users={data?.items ?? []} isLoading={isLoading} />
    </div>
  );
}
