"use client";

import { useAuth } from "@/components/providers/auth-provider";

export default function ProfilePage() {
  const { user } = useAuth();

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-foreground">Profile</h1>
      <p className="text-sm text-muted-foreground">Authenticated account details.</p>

      <div className="rounded-xl border border-border bg-card p-4">
        <div className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <p className="text-muted-foreground">Full name</p>
            <p className="font-medium text-foreground">{user?.full_name || "-"}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Email</p>
            <p className="font-medium text-foreground">{user?.email || "-"}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Role</p>
            <p className="font-medium text-foreground">{user?.is_admin ? "Admin" : "User"}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Plan</p>
            <p className="font-medium text-foreground">{user?.subscription?.plan || "free"}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Credits remaining</p>
            <p className="font-medium text-foreground">
              {user?.subscription?.credits_remaining ?? 0}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
