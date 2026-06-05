"use client";

import { usePets } from "@/hooks/use-pets";
import { useDietPlans } from "@/hooks/use-diet-plans";
import { useApiClient } from "@/hooks/use-api-client";
import { toast } from "sonner";
import { useState } from "react";
import { Download, FileText, Loader2 } from "lucide-react";

const ANON_USER_ID = "00000000-0000-0000-0000-000000000001";

export default function ReportsPage() {
  const { pets } = usePets();
  const { dietPlans } = useDietPlans();
  // Use authenticated API client — includes Clerk JWT in Authorization header
  const apiClient = useApiClient();
  const [downloading, setDownloading] = useState<string | null>(null);
  const plans = dietPlans ?? [];

  const downloadReport = async (planId: string) => {
    const key = planId;
    setDownloading(key);
    try {
      const response = await apiClient.get(`/reports/diet-plan/${planId}/pdf`, {
        responseType: "blob",
      });
      const blobUrl = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = blobUrl;
      link.setAttribute("download", `diet-report-${planId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);
      toast.success("Report downloaded");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to download report");
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Reports</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Download professional PDF diet reports for your veterinarian.
        </p>
      </div>

      {plans.length > 0 ? (
        <div className="space-y-3">
          {plans.map((plan) => {
            const pet = pets?.find((p) => p.id === plan.pet_id);
            const key = plan.id;
            const isDownloadable = plan.user_id !== ANON_USER_ID;
            const petLabel = pet?.name || plan.breed.replace(/_/g, " ").replace(/\b\w/g, (m) => m.toUpperCase()) || "Dog";
            return (
              <div
                key={plan.id}
                className="flex items-center justify-between rounded-xl border border-border bg-card p-4"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <FileText className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="font-medium text-foreground">
                      {petLabel} — Diet Plan
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(plan.created_at).toLocaleDateString()} ·{" "}
                      {plan.daily_calories} kcal/day
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => downloadReport(plan.id)}
                  disabled={downloading === key || !isDownloadable}
                  className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-all hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {downloading === key ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Download className="h-4 w-4" />
                  )}
                  {isDownloadable ? "PDF" : "Not Saved"}
                </button>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-border bg-muted/20 py-16 text-center">
          <p className="text-muted-foreground">No reports available yet.</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Generate a diet plan from Analyze or Diet Plans to create downloadable reports.
          </p>
        </div>
      )}
    </div>
  );
}
