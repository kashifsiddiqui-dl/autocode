"use client";

import { useCallback, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { useCodingStore } from "@/stores/coding-store";
import type { CodingRequest, CodingResult, SSEEvent } from "@/lib/types";
import { toast } from "@/components/ui/toast";

let resultCounter = 0;

export function useCoding() {
  const abortRef = useRef<AbortController | null>(null);
  const store = useCodingStore();

  const handleSSEEvent = useCallback(
    (event: SSEEvent) => {
      switch (event.event) {
        case "session":
          store.startAnalysis(event.data.session_id);
          break;

        case "stage":
          store.addStage(event.data);
          break;

        case "code": {
          const result: CodingResult = {
            id: `result-${++resultCounter}`,
            code: event.data.code,
            description: event.data.description,
            confidence: event.data.confidence,
            reasoning: event.data.reasoning,
            is_billable: event.data.is_billable,
            hierarchy: event.data.hierarchy,
            excludes: event.data.excludes,
            annotations: event.data.annotations,
            seventh_character: event.data.seventh_character,
            status: "suggested",
            source: "ai_suggested",
          };
          store.addResult(result);
          break;
        }

        case "complete":
          store.completeAnalysis(event.data.duration_ms);
          toast({
            title: "Analysis complete",
            description: `Found ${event.data.total_codes} codes in ${(event.data.duration_ms / 1000).toFixed(1)}s`,
            variant: "success",
          });
          break;
      }
    },
    [store],
  );

  const mutation = useMutation({
    mutationFn: async (request: CodingRequest) => {
      // Abort any existing stream
      if (abortRef.current) {
        abortRef.current.abort();
      }

      store.clearResults();

      const controller = await apiClient.analyzeCoding(
        request,
        handleSSEEvent,
        (error) => {
          store.completeAnalysis(0);
          toast({
            title: "Analysis failed",
            description: error.message,
            variant: "destructive",
          });
        },
      );

      abortRef.current = controller;
      return controller;
    },
  });

  const startAnalysis = useCallback(() => {
    const {
      currentInput,
      selectedPatient,
      selectedStandard,
    } = useCodingStore.getState();

    if (!currentInput.trim()) {
      toast({
        title: "No clinical text",
        description: "Please enter clinical notes before analyzing.",
        variant: "destructive",
      });
      return;
    }

    const request: CodingRequest = {
      clinical_text: currentInput,
      patient: selectedPatient
        ? {
            name: selectedPatient.name,
            dob: selectedPatient.dob,
            mrn: selectedPatient.mrn,
            gender: selectedPatient.gender,
          }
        : undefined,
      options: {
        standard: selectedStandard,
      },
    };

    mutation.mutate(request);
  }, [mutation]);

  const cancelAnalysis = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    store.completeAnalysis(0);
  }, [store]);

  return {
    startAnalysis,
    cancelAnalysis,
    isLoading: mutation.isPending || store.isProcessing,
    error: mutation.error,
  };
}
