"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { useSessionStore } from "@/stores/session-store";
import { toast } from "@/components/ui/toast";
import type { SessionStatus } from "@/lib/types";

export function useSessions(params?: {
  page?: number;
  perPage?: number;
  status?: SessionStatus;
}) {
  const store = useSessionStore();

  const query = useQuery({
    queryKey: ["sessions", params?.page, params?.perPage, params?.status],
    queryFn: async () => {
      const result = await apiClient.getSessions({
        page: String(params?.page || 1),
        per_page: String(params?.perPage || 20),
        status: params?.status,
      });
      store.setSessions(result.items, result.total);
      return result;
    },
  });

  return {
    sessions: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    totalPages: query.data?.total_pages ?? 0,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

export function useSession(id: string) {
  const query = useQuery({
    queryKey: ["session", id],
    queryFn: () => apiClient.getSession(id),
    enabled: !!id,
  });

  return {
    session: query.data,
    isLoading: query.isLoading,
    error: query.error,
  };
}

export function useDeleteSession() {
  const queryClient = useQueryClient();
  const store = useSessionStore();

  return useMutation({
    mutationFn: (id: string) => apiClient.deleteSession(id),
    onSuccess: (_, id) => {
      store.removeSession(id);
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      toast({
        title: "Session deleted",
        description: "The coding session has been removed.",
      });
    },
    onError: (error) => {
      toast({
        title: "Delete failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

export function useUpdateResultStatus(sessionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      resultId,
      status,
    }: {
      resultId: string;
      status: string;
    }) => apiClient.updateResult(sessionId, resultId, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["session", sessionId] });
    },
    onError: (error) => {
      toast({
        title: "Update failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}
