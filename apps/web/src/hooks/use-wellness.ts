"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "@/lib/api-client";
import type {
  PaginatedResponse,
  Vaccination,
  VaccinationCreate,
  VaccinationUpdate,
  WellnessSummary,
  WeightLog,
  WeightLogCreate,
} from "@/types";
import { toast } from "sonner";

export function useWellnessSummary() {
  const api = useApiClient();

  const { data, isLoading, error } = useQuery<WellnessSummary>({
    queryKey: ["wellness", "summary"],
    queryFn: async () => {
      const res = await api.get("/wellness/summary");
      return res.data;
    },
  });

  return { summary: data, isLoading, error };
}

export function useWeightLogs(petId?: string, page = 1, pageSize = 5) {
  const api = useApiClient();

  const { data, isLoading, error } = useQuery<PaginatedResponse<WeightLog>>({
    queryKey: ["wellness", "weights", petId, page, pageSize],
    queryFn: async () => {
      const res = await api.get(`/wellness/pets/${petId}/weights?page=${page}&page_size=${pageSize}`);
      return res.data;
    },
    enabled: !!petId,
  });

  return { data, isLoading, error };
}

export function useCreateWeightLog(petId?: string) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: WeightLogCreate) => {
      if (!petId) throw new Error("Select a pet first");
      const res = await api.post(`/wellness/pets/${petId}/weights`, payload);
      return res.data as WeightLog;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wellness", "weights", petId] });
      queryClient.invalidateQueries({ queryKey: ["wellness", "summary"] });
      toast.success("Weight log added");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useDeleteWeightLog(petId?: string) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (logId: string) => {
      await api.delete(`/wellness/weights/${logId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wellness", "weights", petId] });
      queryClient.invalidateQueries({ queryKey: ["wellness", "summary"] });
      toast.success("Weight log removed");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useVaccinations(petId?: string, page = 1, pageSize = 5) {
  const api = useApiClient();

  const { data, isLoading, error } = useQuery<PaginatedResponse<Vaccination>>({
    queryKey: ["wellness", "vaccinations", petId, page, pageSize],
    queryFn: async () => {
      const res = await api.get(
        `/wellness/pets/${petId}/vaccinations?page=${page}&page_size=${pageSize}`
      );
      return res.data;
    },
    enabled: !!petId,
  });

  return { data, isLoading, error };
}

export function useCreateVaccination(petId?: string) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: VaccinationCreate) => {
      if (!petId) throw new Error("Select a pet first");
      const res = await api.post(`/wellness/pets/${petId}/vaccinations`, payload);
      return res.data as Vaccination;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wellness", "vaccinations", petId] });
      queryClient.invalidateQueries({ queryKey: ["wellness", "summary"] });
      toast.success("Vaccination added");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useUpdateVaccination(petId?: string) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: VaccinationUpdate }) => {
      const res = await api.patch(`/wellness/vaccinations/${id}`, payload);
      return res.data as Vaccination;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wellness", "vaccinations", petId] });
      queryClient.invalidateQueries({ queryKey: ["wellness", "summary"] });
      toast.success("Vaccination updated");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useDeleteVaccination(petId?: string) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (vaccinationId: string) => {
      await api.delete(`/wellness/vaccinations/${vaccinationId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wellness", "vaccinations", petId] });
      queryClient.invalidateQueries({ queryKey: ["wellness", "summary"] });
      toast.success("Vaccination removed");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}
