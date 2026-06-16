"use client";

import { CheckCircle2, Download, Loader2, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { CodeCard } from "./CodeCard";
import { useCodingStore } from "@/stores/coding-store";
import { cn } from "@/lib/utils";
import type { SSEStageEvent } from "@/lib/types";

const stageLabels: Record<string, string> = {
  retrieval: "Retrieving candidates",
  reranking: "Reranking results",
  analysis: "AI analysis",
  validation: "Validating codes",
};

function StageIndicator({ stage }: { stage: SSEStageEvent }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      {stage.status === "started" ? (
        <Loader2 className="h-4 w-4 animate-spin text-primary-500" />
      ) : (
        <CheckCircle2 className="h-4 w-4 text-green-500" />
      )}
      <span
        className={cn(
          stage.status === "completed"
            ? "text-neutral-600 dark:text-neutral-400"
            : "font-medium text-neutral-900 dark:text-white",
        )}
      >
        {stageLabels[stage.stage] || stage.stage}
      </span>
      {stage.duration_ms != null && (
        <span className="text-xs text-neutral-400">
          {(stage.duration_ms / 1000).toFixed(1)}s
        </span>
      )}
      {stage.candidates != null && (
        <Badge variant="secondary" className="text-[10px]">
          {stage.candidates} candidates
        </Badge>
      )}
    </div>
  );
}

interface CodingResultsProps {
  onExport?: () => void;
}

export function CodingResults({ onExport }: CodingResultsProps) {
  const {
    results,
    stages,
    isProcessing,
    totalDurationMs,
    updateResultStatus,
  } = useCodingStore();

  const hasResults = results.length > 0 || stages.length > 0;

  if (!hasResults) return null;

  const acceptedCount = results.filter((r) => r.status === "accepted").length;
  const rejectedCount = results.filter((r) => r.status === "rejected").length;
  const suggestedCount = results.filter((r) => r.status === "suggested").length;

  const highConfidence = results.filter((r) => r.confidence >= 0.8).length;
  const medConfidence = results.filter(
    (r) => r.confidence >= 0.5 && r.confidence < 0.8,
  ).length;
  const lowConfidence = results.filter((r) => r.confidence < 0.5).length;

  const handleAcceptAll = () => {
    results.forEach((r) => {
      if (r.status === "suggested" && r.confidence >= 0.8) {
        updateResultStatus(r.id, "accepted");
      }
    });
  };

  return (
    <div className="space-y-4">
      {/* Pipeline stages */}
      {stages.length > 0 && (
        <div className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
          <h3 className="mb-3 text-sm font-semibold text-neutral-900 dark:text-white">
            Processing Pipeline
          </h3>
          <div className="space-y-2">
            {stages.map((stage, i) => (
              <StageIndicator key={`${stage.stage}-${stage.status}-${i}`} stage={stage} />
            ))}
          </div>
        </div>
      )}

      {/* Loading skeleton */}
      {isProcessing && results.length === 0 && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900"
            >
              <div className="flex items-start gap-3">
                <Skeleton className="h-8 w-20 rounded-full" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                  <Skeleton className="h-2 w-full" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Results header with stats */}
      {results.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-neutral-200 bg-white px-4 py-3 dark:border-neutral-800 dark:bg-neutral-900">
          <div className="flex items-center gap-3">
            <h3 className="text-sm font-semibold text-neutral-900 dark:text-white">
              {results.length} Code{results.length !== 1 ? "s" : ""} Found
            </h3>
            {totalDurationMs != null && (
              <span className="text-xs text-neutral-400">
                in {(totalDurationMs / 1000).toFixed(1)}s
              </span>
            )}
            <div className="flex items-center gap-2">
              {highConfidence > 0 && (
                <Badge variant="success" className="text-[10px]">
                  {highConfidence} high
                </Badge>
              )}
              {medConfidence > 0 && (
                <Badge variant="warning" className="text-[10px]">
                  {medConfidence} medium
                </Badge>
              )}
              {lowConfidence > 0 && (
                <Badge variant="destructive" className="text-[10px]">
                  {lowConfidence} low
                </Badge>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {suggestedCount > 0 && (
              <Button variant="outline" size="sm" onClick={handleAcceptAll}>
                <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />
                Accept High Confidence
              </Button>
            )}
            {onExport && (
              <Button variant="outline" size="sm" onClick={onExport}>
                <Download className="mr-1.5 h-3.5 w-3.5" />
                Export
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Code cards */}
      <div className="space-y-3">
        {results.map((result, index) => (
          <div
            key={result.id}
            className="code-card-enter"
            style={{ animationDelay: `${index * 50}ms` }}
          >
            <CodeCard
              result={result}
              onAccept={() => updateResultStatus(result.id, "accepted")}
              onReject={() => updateResultStatus(result.id, "rejected")}
            />
          </div>
        ))}
      </div>

      {/* Completion banner */}
      {!isProcessing && results.length > 0 && (
        <div className="rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-600 dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-400">
          <div className="flex items-center gap-4">
            <span>
              <CheckCircle2 className="mr-1 inline h-4 w-4 text-green-500" />
              {acceptedCount} accepted
            </span>
            <span>
              <XCircle className="mr-1 inline h-4 w-4 text-red-400" />
              {rejectedCount} rejected
            </span>
            <span>{suggestedCount} pending review</span>
          </div>
        </div>
      )}
    </div>
  );
}
