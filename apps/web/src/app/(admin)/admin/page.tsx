"use client";

import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "@/lib/api-client";
import { BarChart3, Dog, Sparkles, FileText, Users } from "lucide-react";
import { StatsCard } from "@/components/admin/stats-card";

interface AdminStats {
  users: number;
  pets: number;
  predictions: number;
  diet_plans: number;
}

export default function AdminPage() {
  const api = useApiClient();

  const { data: stats, isLoading } = useQuery<AdminStats>({
    queryKey: ["admin-stats"],
    queryFn: async () => {
      const res = await api.get("/admin/stats");
      return res.data;
    },
  });

  const cards = [
    { label: "Total Users", value: stats?.users, icon: Users, color: "text-primary" },
    { label: "Total Pets", value: stats?.pets, icon: Dog, color: "text-emerald-500" },
    {
      label: "AI Analyses",
      value: stats?.predictions,
      icon: Sparkles,
      color: "text-amber-500",
    },
    {
      label: "Diet Plans",
      value: stats?.diet_plans,
      icon: FileText,
      color: "text-rose-500",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <BarChart3 className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-bold text-foreground">Platform Overview</h1>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card) => (
          <StatsCard key={card.label} {...card} isLoading={isLoading} />
        ))}
      </div>
    </div>
  );
}
