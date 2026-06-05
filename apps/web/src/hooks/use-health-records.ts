"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useApiClient } from "@/lib/api-client";
import type {
  ExpenseCreate,
  ExpenseEntry,
  ExpenseUpdate,
  HealthRecord,
  HealthRecordCreate,
  HealthRecordUpdate,
  HealthReminder,
  HealthSummary,
  MedicationCreate,
  MedicationSchedule,
  MedicationUpdate,
  PaginatedResponse,
} from "@/types";
import { toast } from "sonner";

export function useHealthSummary() {
  const api = useApiClient();
  const { data, isLoading, error } = useQuery<HealthSummary>({
    queryKey: ["health-records", "summary"],
    queryFn: async () => {
      const res = await api.get("/health-records/summary");
      return res.data;
    },
  });

  return { summary: data, isLoading, error };
}

export function useHealthReminders(windowDays = 30, limit = 40) {
  const api = useApiClient();
  const { data, isLoading, error } = useQuery<HealthReminder[]>({
    queryKey: ["health-records", "reminders", windowDays, limit],
    queryFn: async () => {
      const res = await api.get(`/health-records/reminders?window_days=${windowDays}&limit=${limit}`);
      return res.data;
    },
  });

  return { reminders: data, isLoading, error };
}

export function useHealthRecords(petId?: string, page = 1, pageSize = 10) {
  const api = useApiClient();

  const { data, isLoading, error } = useQuery<PaginatedResponse<HealthRecord>>({
    queryKey: ["health-records", "records", petId, page, pageSize],
    queryFn: async () => {
      const res = await api.get(`/health-records/pets/${petId}/records?page=${page}&page_size=${pageSize}`);
      return res.data;
    },
    enabled: !!petId,
  });

  return { data, isLoading, error };
}

export function useCreateHealthRecord(petId?: string) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: HealthRecordCreate) => {
      if (!petId) throw new Error("Select a pet first");
      const res = await api.post(`/health-records/pets/${petId}/records`, payload);
      return res.data as HealthRecord;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["health-records", "records", petId] });
      queryClient.invalidateQueries({ queryKey: ["health-records", "summary"] });
      queryClient.invalidateQueries({ queryKey: ["health-records", "reminders"] });
      toast.success("Health record added");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useUpdateHealthRecord(petId?: string) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: HealthRecordUpdate }) => {
      const res = await api.patch(`/health-records/records/${id}`, payload);
      return res.data as HealthRecord;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["health-records", "records", petId] });
      queryClient.invalidateQueries({ queryKey: ["health-records", "summary"] });
      queryClient.invalidateQueries({ queryKey: ["health-records", "reminders"] });
      toast.success("Health record updated");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useDeleteHealthRecord(petId?: string) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (recordId: string) => {
      await api.delete(`/health-records/records/${recordId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["health-records", "records", petId] });
      queryClient.invalidateQueries({ queryKey: ["health-records", "summary"] });
      queryClient.invalidateQueries({ queryKey: ["health-records", "reminders"] });
      toast.success("Health record removed");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useMedications(petId?: string, page = 1, pageSize = 10) {
  const api = useApiClient();

  const { data, isLoading, error } = useQuery<PaginatedResponse<MedicationSchedule>>({
    queryKey: ["health-records", "medications", petId, page, pageSize],
    queryFn: async () => {
      const res = await api.get(
        `/health-records/pets/${petId}/medications?page=${page}&page_size=${pageSize}`
      );
      return res.data;
    },
    enabled: !!petId,
  });

  return { data, isLoading, error };
}

export function useCreateMedication(petId?: string) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: MedicationCreate) => {
      if (!petId) throw new Error("Select a pet first");
      const res = await api.post(`/health-records/pets/${petId}/medications`, payload);
      return res.data as MedicationSchedule;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["health-records", "medications", petId] });
      queryClient.invalidateQueries({ queryKey: ["health-records", "summary"] });
      queryClient.invalidateQueries({ queryKey: ["health-records", "reminders"] });
      toast.success("Medication schedule added");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useUpdateMedication(petId?: string) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: MedicationUpdate }) => {
      const res = await api.patch(`/health-records/medications/${id}`, payload);
      return res.data as MedicationSchedule;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["health-records", "medications", petId] });
      queryClient.invalidateQueries({ queryKey: ["health-records", "summary"] });
      queryClient.invalidateQueries({ queryKey: ["health-records", "reminders"] });
      toast.success("Medication schedule updated");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useDeleteMedication(petId?: string) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/health-records/medications/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["health-records", "medications", petId] });
      queryClient.invalidateQueries({ queryKey: ["health-records", "summary"] });
      queryClient.invalidateQueries({ queryKey: ["health-records", "reminders"] });
      toast.success("Medication schedule removed");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useExpenses(petId?: string, page = 1, pageSize = 10) {
  const api = useApiClient();

  const { data, isLoading, error } = useQuery<PaginatedResponse<ExpenseEntry>>({
    queryKey: ["health-records", "expenses", petId, page, pageSize],
    queryFn: async () => {
      const res = await api.get(`/health-records/pets/${petId}/expenses?page=${page}&page_size=${pageSize}`);
      return res.data;
    },
    enabled: !!petId,
  });

  return { data, isLoading, error };
}

export function useCreateExpense(petId?: string) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: ExpenseCreate) => {
      if (!petId) throw new Error("Select a pet first");
      const res = await api.post(`/health-records/pets/${petId}/expenses`, payload);
      return res.data as ExpenseEntry;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["health-records", "expenses", petId] });
      queryClient.invalidateQueries({ queryKey: ["health-records", "summary"] });
      toast.success("Expense added");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useUpdateExpense(petId?: string) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: ExpenseUpdate }) => {
      const res = await api.patch(`/health-records/expenses/${id}`, payload);
      return res.data as ExpenseEntry;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["health-records", "expenses", petId] });
      queryClient.invalidateQueries({ queryKey: ["health-records", "summary"] });
      toast.success("Expense updated");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}

export function useDeleteExpense(petId?: string) {
  const api = useApiClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/health-records/expenses/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["health-records", "expenses", petId] });
      queryClient.invalidateQueries({ queryKey: ["health-records", "summary"] });
      toast.success("Expense removed");
    },
    onError: (err: Error) => toast.error(err.message),
  });
}
