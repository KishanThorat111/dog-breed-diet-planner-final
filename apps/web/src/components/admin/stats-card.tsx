"use client";

import type { LucideIcon } from "lucide-react";
import { Loader2 } from "lucide-react";

interface StatsCardProps {
  label: string;
  value: number | undefined;
  icon: LucideIcon;
  color: string;
  isLoading?: boolean;
}

export function StatsCard({ label, value, icon: Icon, color, isLoading }: StatsCardProps) {
  return (
    <div className="rounded-2xl border border-border bg-card p-5">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">{label}</span>
        <Icon className={`h-4 w-4 ${color}`} />
      </div>
      <p className="mt-3 text-3xl font-bold text-foreground">
        {isLoading ? (
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        ) : (
          value?.toLocaleString() ?? "—"
        )}
      </p>
    </div>
  );
}
