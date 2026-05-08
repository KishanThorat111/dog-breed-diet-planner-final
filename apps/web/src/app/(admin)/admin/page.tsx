"use client";

import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import { BarChart3, Dog, Sparkles, FileText, Users } from "lucide-react";
import { StatsCard } from "@/components/admin/stats-card";

interface AdminStats {
  total_users: number;
  total_pets: number;
  total_predictions: number;
  total_diet_plans: number;
}

export default function AdminPage() {
  const { data: stats, isLoading } = useQuery<AdminStats>({
    queryKey: ["admin-stats"],
    queryFn: async () => {
      const res = await apiClient.get("/admin/stats");
      return res.data;
    },
  });

  const cards = [
    { label: "Total Users", value: stats?.total_users, icon: Users, color: "text-primary" },
    { label: "Total Pets", value: stats?.total_pets, icon: Dog, color: "text-emerald-500" },
    {
      label: "AI Analyses",
      value: stats?.total_predictions,
      icon: Sparkles,
      color: "text-amber-500",
    },
    {
      label: "Diet Plans",
      value: stats?.total_diet_plans,
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
