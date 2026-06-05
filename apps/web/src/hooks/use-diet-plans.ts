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
        const injectIntoCache = (old: PaginatedResponse<DietPlan> | undefined): PaginatedResponse<DietPlan> => {
          const prevItems = old?.items ?? [];
          const pageSize = old?.page_size ?? 10;
          const total = (old?.total ?? 0) + 1;
          const newItems = [plan, ...prevItems].slice(0, pageSize);

          return {
            items: newItems,
            total,
            page: old?.page ?? 1,
            page_size: pageSize,
            pages: Math.max(old?.pages ?? 1, Math.ceil(total / pageSize)),
          };
        };

        // Keep both legacy and current key shapes in sync.
        queryClient.setQueryData(["diet-plans", undefined], injectIntoCache);
        queryClient.setQueryData(["diet-plans"], injectIntoCache);
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
