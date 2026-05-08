"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "@/lib/api-client";
import type { Prediction, PaginatedResponse } from "@/types";
import { toast } from "sonner";

export function usePredictions() {
  const api = useApiClient();

  const { data, isLoading } = useQuery<PaginatedResponse<Prediction>>({
    queryKey: ["predictions"],
    queryFn: async () => {
      const res = await api.get("/predictions");
      return res.data;
    },
  });

  return { predictions: data?.items, isLoading };
}

export function useAnalyzeImage() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ file, petId }: { file: File; petId?: string }) => {
      const formData = new FormData();
      formData.append("file", file);
      if (petId) formData.append("pet_id", petId);

      const res = await api.post("/predictions/analyze", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return res.data as Prediction;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["predictions"] });
    },
    onError: (err: Error) => {
      toast.error(err.message || "Analysis failed");
    },
  });
}
