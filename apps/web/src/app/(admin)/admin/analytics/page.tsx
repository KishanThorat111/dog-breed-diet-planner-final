"use client";

import { useQuery } from "@tanstack/react-query";
import { useApiClient } from "@/lib/api-client";
import { Activity, CreditCard, Syringe, TrendingUp, Weight } from "lucide-react";

interface GrowthPoint {
  month: string;
  count: number;
}

interface AnalyticsData {
  user_growth: GrowthPoint[];
  pet_growth: GrowthPoint[];
  wellness: {
    upcoming_vaccinations: number;
    overdue_vaccinations: number;
    active_medications: number;
    health_records: number;
    weight_logs: number;
    monthly_expense_total: number;
  };
  ai_usage_7d: {
    events: number;
    tokens: number;
  };
}

export default function AdminAnalyticsPage() {
  const api = useApiClient();

  const { data, isLoading } = useQuery<AnalyticsData>({
    queryKey: ["admin-analytics"],
    queryFn: async () => {
      const res = await api.get("/admin/analytics");
      return res.data;
    },
  });

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading analytics...</p>;
  }

  const wellness = data?.wellness;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Advanced Analytics</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Growth trends, wellness insights, and AI usage telemetry.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[
          {
            label: "Upcoming Vaccinations",
            value: wellness?.upcoming_vaccinations ?? 0,
            icon: Syringe,
            color: "text-amber-600",
          },
          {
            label: "Overdue Vaccinations",
            value: wellness?.overdue_vaccinations ?? 0,
            icon: Syringe,
            color: "text-rose-600",
          },
          {
            label: "Active Medications",
            value: wellness?.active_medications ?? 0,
            icon: Activity,
            color: "text-sky-600",
          },
          {
            label: "Health Records",
            value: wellness?.health_records ?? 0,
            icon: Activity,
            color: "text-emerald-600",
          },
          {
            label: "Weight Logs",
            value: wellness?.weight_logs ?? 0,
            icon: Weight,
            color: "text-indigo-600",
          },
          {
            label: "Monthly Expense",
            value: `₹${(wellness?.monthly_expense_total ?? 0).toLocaleString()}`,
            icon: CreditCard,
            color: "text-violet-600",
          },
        ].map((item) => (
          <article key={item.label} className="rounded-xl border border-border bg-card p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase tracking-wide text-muted-foreground">{item.label}</span>
              <item.icon className={`h-4 w-4 ${item.color}`} />
            </div>
            <p className="mt-3 text-2xl font-bold text-foreground">{item.value}</p>
          </article>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-border bg-card p-4">
          <h2 className="mb-3 text-base font-semibold text-foreground">User Growth (6 months)</h2>
          <div className="space-y-2">
            {data?.user_growth?.map((point) => (
              <div key={point.month} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{point.month}</span>
                <span className="font-medium text-foreground">{point.count}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-border bg-card p-4">
          <h2 className="mb-3 text-base font-semibold text-foreground">Pet Growth (6 months)</h2>
          <div className="space-y-2">
            {data?.pet_growth?.map((point) => (
              <div key={point.month} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{point.month}</span>
                <span className="font-medium text-foreground">{point.count}</span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="rounded-xl border border-border bg-card p-4">
        <div className="flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-primary" />
          <h2 className="text-base font-semibold text-foreground">AI Usage (7 days)</h2>
        </div>
        <p className="mt-3 text-sm text-muted-foreground">
          Events: <span className="font-medium text-foreground">{data?.ai_usage_7d.events ?? 0}</span> · Tokens: <span className="font-medium text-foreground">{data?.ai_usage_7d.tokens ?? 0}</span>
        </p>
      </section>
    </div>
  );
}
