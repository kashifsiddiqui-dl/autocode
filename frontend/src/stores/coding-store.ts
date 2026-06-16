"use client";

import { create } from "zustand";
import type {
  CodingResult,
  CodingStandard,
  LLMProvider,
  Patient,
  SSEStageEvent,
} from "@/lib/types";

interface CodingState {
  // Input state
  currentInput: string;
  selectedPatient: Patient | null;
  selectedStandard: CodingStandard;
  llmProvider: LLMProvider;

  // Processing state
  isProcessing: boolean;
  streamingText: string;
  currentSessionId: string | null;
  stages: SSEStageEvent[];

  // Results
  results: CodingResult[];
  totalDurationMs: number | null;

  // Actions
  setInput: (text: string) => void;
  setPatient: (patient: Patient | null) => void;
  setStandard: (standard: CodingStandard) => void;
  setProvider: (provider: LLMProvider) => void;
  startAnalysis: (sessionId: string) => void;
  addStage: (stage: SSEStageEvent) => void;
  addResult: (result: CodingResult) => void;
  updateResultStatus: (
    resultId: string,
    status: "accepted" | "rejected",
  ) => void;
  setStreamingText: (text: string) => void;
  completeAnalysis: (durationMs: number) => void;
  clearResults: () => void;
  reset: () => void;
}

export const useCodingStore = create<CodingState>((set) => ({
  // Initial state
  currentInput: "",
  selectedPatient: null,
  selectedStandard: "icd10cm",
  llmProvider: "anthropic",
  isProcessing: false,
  streamingText: "",
  currentSessionId: null,
  stages: [],
  results: [],
  totalDurationMs: null,

  // Actions
  setInput: (text) => set({ currentInput: text }),
  setPatient: (patient) => set({ selectedPatient: patient }),
  setStandard: (standard) => set({ selectedStandard: standard }),
  setProvider: (provider) => set({ llmProvider: provider }),

  startAnalysis: (sessionId) =>
    set({
      isProcessing: true,
      streamingText: "",
      currentSessionId: sessionId,
      stages: [],
      results: [],
      totalDurationMs: null,
    }),

  addStage: (stage) =>
    set((state) => {
      const existing = state.stages.findIndex(
        (s) => s.stage === stage.stage && s.status !== stage.status,
      );
      if (existing >= 0) {
        const updated = [...state.stages];
        updated[existing] = stage;
        return { stages: updated };
      }
      return { stages: [...state.stages, stage] };
    }),

  addResult: (result) =>
    set((state) => ({
      results: [...state.results, result],
    })),

  updateResultStatus: (resultId, status) =>
    set((state) => ({
      results: state.results.map((r) =>
        r.id === resultId ? { ...r, status } : r,
      ),
    })),

  setStreamingText: (text) => set({ streamingText: text }),

  completeAnalysis: (durationMs) =>
    set({
      isProcessing: false,
      totalDurationMs: durationMs,
    }),

  clearResults: () =>
    set({
      results: [],
      stages: [],
      streamingText: "",
      currentSessionId: null,
      totalDurationMs: null,
    }),

  reset: () =>
    set({
      currentInput: "",
      selectedPatient: null,
      selectedStandard: "icd10cm",
      llmProvider: "anthropic",
      isProcessing: false,
      streamingText: "",
      currentSessionId: null,
      stages: [],
      results: [],
      totalDurationMs: null,
    }),
}));
