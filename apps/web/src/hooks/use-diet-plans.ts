"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "@/lib/api-client";
import type { DietPlan, GenerateDietPlanRequest, PaginatedResponse } from "@/types";
import { toast } from "sonner";

export function useDietPlans(petId?: string) {
  const api = useApiClient();

  const { data, isLoading } = useQuery<PaginatedResponse<DietPlan>>({
    queryKey: ["diet-plans", petId],
    queryFn: async () => {
      const url = petId ? `/diet-plans?pet_id=${petId}` : "/diet-plans";
      const res = await api.get(url);
      return res.data;
    },
  });

  return { dietPlans: data?.items, total: data?.total, isLoading };
}

export function useGenerateDietPlan() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: GenerateDietPlanRequest) => {
      const res = await api.post("/diet-plans/generate", request);
      return res.data as DietPlan;
    },
    onSuccess: (plan: DietPlan) => {
      const ANON_ID = "00000000-0000-0000-0000-000000000001";
      // If the plan is anonymous (quick-generate), inject it into the local cache
      if (plan.user_id === ANON_ID) {
        queryClient.setQueryData(["diet-plans"], (old: PaginatedResponse<DietPlan> | undefined) => {
          const prevItems = old?.items ?? [];
          const newItems = [plan, ...prevItems];
          return {
            items: newItems,
            total: (old?.total ?? 0) + 1,
            page: old?.page ?? 1,
            page_size: old?.page_size ?? 10,
            pages: Math.ceil(((old?.total ?? 0) + 1) / (old?.page_size ?? 10)),
          } as PaginatedResponse<DietPlan>;
        });
      } else {
        queryClient.invalidateQueries({ queryKey: ["diet-plans"] });
      }

      toast.success("Diet plan generated");
    },
    onError: (err: Error) => {
      toast.error(err.message || "Failed to generate diet plan");
    },
  });
}
