"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "@/lib/api-client";
import type { Pet, PetCreate, PaginatedResponse } from "@/types";
import { toast } from "sonner";

export function usePets() {
  const api = useApiClient();

  const { data, isLoading, error } = useQuery<PaginatedResponse<Pet>>({
    queryKey: ["pets"],
    queryFn: async () => {
      const res = await api.get("/pets");
      return res.data;
    },
  });

  return { pets: data?.items, total: data?.total, isLoading, error };
}

export function usePet(id: string) {
  const api = useApiClient();

  return useQuery<Pet>({
    queryKey: ["pets", id],
    queryFn: async () => {
      const res = await api.get(`/pets/${id}`);
      return res.data;
    },
    enabled: !!id,
  });
}

export function useCreatePet() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: PetCreate) => {
      const res = await api.post("/pets", data);
      return res.data as Pet;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pets"] });
      toast.success("Pet added successfully");
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });
}

export function useUpdatePet(id: string) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: Partial<PetCreate>) => {
      const res = await api.patch(`/pets/${id}`, data);
      return res.data as Pet;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pets"] });
      queryClient.invalidateQueries({ queryKey: ["pets", id] });
      toast.success("Pet updated");
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });
}

export function useDeletePet() {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/pets/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pets"] });
      toast.success("Pet removed");
    },
    onError: (err: Error) => {
      toast.error(err.message);
    },
  });
}
