"use client";

import { create } from "zustand";
import type { CodingSessionList, SessionStatus } from "@/lib/types";

interface SessionFilters {
  status?: SessionStatus;
  dateFrom?: string;
  dateTo?: string;
}

interface SessionState {
  sessions: CodingSessionList[];
  totalSessions: number;
  currentPage: number;
  perPage: number;
  filters: SessionFilters;
  isLoading: boolean;

  // Actions
  setSessions: (sessions: CodingSessionList[], total: number) => void;
  setPage: (page: number) => void;
  setFilters: (filters: SessionFilters) => void;
  setLoading: (loading: boolean) => void;
  removeSession: (id: string) => void;
  reset: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  sessions: [],
  totalSessions: 0,
  currentPage: 1,
  perPage: 20,
  filters: {},
  isLoading: false,

  setSessions: (sessions, total) =>
    set({ sessions, totalSessions: total }),

  setPage: (page) => set({ currentPage: page }),

  setFilters: (filters) =>
    set({ filters, currentPage: 1 }),

  setLoading: (loading) => set({ isLoading: loading }),

  removeSession: (id) =>
    set((state) => ({
      sessions: state.sessions.filter((s) => s.id !== id),
      totalSessions: state.totalSessions - 1,
    })),

  reset: () =>
    set({
      sessions: [],
      totalSessions: 0,
      currentPage: 1,
      filters: {},
      isLoading: false,
    }),
}));
