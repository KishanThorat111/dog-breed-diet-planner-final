"use client";

import type { User } from "@/types";
import { Loader2 } from "lucide-react";

interface UserTableProps {
  users: User[];
  isLoading: boolean;
}

export function UserTable({ users, isLoading }: UserTableProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-border">
      <table className="w-full text-sm">
        <thead className="border-b border-border bg-muted/30">
          <tr>
            {["Email", "Name", "Admin", "Active", "Joined"].map((h) => (
              <th key={h} className="px-4 py-3 text-left font-medium text-muted-foreground">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id} className="border-b border-border last:border-0 hover:bg-muted/20 transition-colors">
              <td className="px-4 py-3 text-foreground">{user.email}</td>
              <td className="px-4 py-3 text-muted-foreground">{user.full_name ?? "—"}</td>
              <td className="px-4 py-3">
                {user.is_admin ? (
                  <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                    Admin
                  </span>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </td>
              <td className="px-4 py-3">
                <span
                  className={`inline-block h-2 w-2 rounded-full ${
                    user.is_active ? "bg-emerald-500" : "bg-muted-foreground"
                  }`}
                />
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {new Date(user.created_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {users.length === 0 && (
        <div className="py-12 text-center text-sm text-muted-foreground">No users found.</div>
      )}
    </div>
  );
}
