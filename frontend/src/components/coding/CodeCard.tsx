"use client";

import { useState } from "react";
import {
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronRight,
  CircleDot,
  Info,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { CodingResult } from "@/lib/types";

interface CodeCardProps {
  result: CodingResult;
  onAccept: () => void;
  onReject: () => void;
}

function confidenceColor(c: number) {
  if (c >= 0.8) return "bg-green-500";
  if (c >= 0.5) return "bg-amber-500";
  return "bg-red-500";
}

function confidenceBadgeVariant(c: number): "success" | "warning" | "destructive" {
  if (c >= 0.8) return "success";
  if (c >= 0.5) return "warning";
  return "destructive";
}

export function CodeCard({ result, onAccept, onReject }: CodeCardProps) {
  const [showReasoning, setShowReasoning] = useState(false);
  const [showInstructions, setShowInstructions] = useState(false);

  const isAccepted = result.status === "accepted";
  const isRejected = result.status === "rejected";

  return (
    <div
      className={cn(
        "rounded-lg border bg-white transition-all dark:bg-neutral-900",
        isAccepted &&
          "border-green-200 bg-green-50/50 dark:border-green-800 dark:bg-green-950/30",
        isRejected &&
          "border-red-200 bg-red-50/30 opacity-60 dark:border-red-900 dark:bg-red-950/20",
        !isAccepted &&
          !isRejected &&
          "border-neutral-200 dark:border-neutral-800",
      )}
    >
      <div className="p-4">
        {/* Top row: code badge, description, actions */}
        <div className="flex items-start gap-3">
          {/* Code badge */}
          <Badge
            variant={confidenceBadgeVariant(result.confidence)}
            className="shrink-0 px-3 py-1 text-sm font-bold"
          >
            {result.code}
          </Badge>

          {/* Description + hierarchy */}
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-neutral-900 dark:text-white">
              {result.description}
            </p>

            {/* Hierarchy breadcrumb */}
            {result.hierarchy && (
              <p className="mt-1 text-xs text-neutral-500">
                Ch. {result.hierarchy.chapter}: {result.hierarchy.chapter_description}
                <span className="mx-1 text-neutral-300 dark:text-neutral-600">/</span>
                {result.hierarchy.section_description}
                <span className="mx-1 text-neutral-300 dark:text-neutral-600">/</span>
                {result.hierarchy.category}
              </p>
            )}

            {/* Confidence bar */}
            <div className="mt-2 flex items-center gap-2">
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-neutral-100 dark:bg-neutral-800">
                <div
                  className={cn(
                    "h-full rounded-full transition-all",
                    confidenceColor(result.confidence),
                  )}
                  style={{ width: `${result.confidence * 100}%` }}
                />
              </div>
              <span className="text-xs font-medium tabular-nums text-neutral-600 dark:text-neutral-400">
                {(result.confidence * 100).toFixed(0)}%
              </span>

              {/* Billable indicator */}
              {result.is_billable ? (
                <Badge variant="success" className="text-[10px]">
                  <Check className="mr-0.5 h-2.5 w-2.5" /> Billable
                </Badge>
              ) : (
                <Badge variant="warning" className="text-[10px]">
                  <AlertTriangle className="mr-0.5 h-2.5 w-2.5" /> Non-billable
                </Badge>
              )}
            </div>
          </div>

          {/* Accept / Reject buttons */}
          <div className="flex shrink-0 items-center gap-1">
            <Button
              variant={isAccepted ? "default" : "outline"}
              size="icon"
              className={cn(
                "h-8 w-8",
                isAccepted &&
                  "bg-green-600 text-white hover:bg-green-700",
              )}
              onClick={onAccept}
              title="Accept"
            >
              <Check className="h-4 w-4" />
            </Button>
            <Button
              variant={isRejected ? "destructive" : "outline"}
              size="icon"
              className="h-8 w-8"
              onClick={onReject}
              title="Reject"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* 7th character display */}
        {result.seventh_character && result.seventh_character.length > 0 && (
          <div className="mt-3 rounded-md bg-primary-50 px-3 py-2 dark:bg-primary-950">
            <p className="text-xs font-semibold text-primary-700 dark:text-primary-300">
              7th Character Required
            </p>
            <div className="mt-1 flex flex-wrap gap-1">
              {result.seventh_character.map((sc) => (
                <Badge key={sc.character} variant="outline" className="text-[10px]">
                  {sc.character}: {sc.description}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Excludes warnings */}
        {result.excludes?.excludes1 && result.excludes.excludes1.length > 0 && (
          <div className="mt-3 rounded-md bg-red-50 px-3 py-2 dark:bg-red-950/50">
            <p className="text-xs font-semibold text-red-700 dark:text-red-400">
              <AlertTriangle className="mr-1 inline h-3 w-3" />
              Excludes1 (mutually exclusive)
            </p>
            <p className="mt-0.5 text-xs text-red-600 dark:text-red-400">
              {result.excludes.excludes1.join(", ")}
            </p>
          </div>
        )}

        {result.excludes?.excludes2 && result.excludes.excludes2.length > 0 && (
          <div className="mt-2 rounded-md bg-amber-50 px-3 py-2 dark:bg-amber-950/50">
            <p className="text-xs font-semibold text-amber-700 dark:text-amber-400">
              <Info className="mr-1 inline h-3 w-3" />
              Excludes2 (not included here)
            </p>
            <p className="mt-0.5 text-xs text-amber-600 dark:text-amber-400">
              {result.excludes.excludes2.join(", ")}
            </p>
          </div>
        )}

        {/* Expandable sections */}
        <div className="mt-3 space-y-1">
          {/* Reasoning */}
          <button
            className="flex w-full items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-neutral-600 transition-colors hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800"
            onClick={() => setShowReasoning(!showReasoning)}
          >
            {showReasoning ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )}
            AI Reasoning
          </button>
          {showReasoning && (
            <div className="rounded-md bg-neutral-50 px-3 py-2 text-xs leading-relaxed text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300">
              {result.reasoning}
            </div>
          )}

          {/* Coding instructions */}
          {result.annotations && (
            <>
              <button
                className="flex w-full items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-neutral-600 transition-colors hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-800"
                onClick={() => setShowInstructions(!showInstructions)}
              >
                {showInstructions ? (
                  <ChevronDown className="h-3.5 w-3.5" />
                ) : (
                  <ChevronRight className="h-3.5 w-3.5" />
                )}
                Coding Instructions
              </button>
              {showInstructions && (
                <div className="space-y-2 rounded-md bg-neutral-50 px-3 py-2 text-xs dark:bg-neutral-800">
                  {result.annotations.code_first && (
                    <p className="text-neutral-700 dark:text-neutral-300">
                      <span className="font-semibold">Code first:</span>{" "}
                      {result.annotations.code_first}
                    </p>
                  )}
                  {result.annotations.use_additional && (
                    <p className="text-neutral-700 dark:text-neutral-300">
                      <span className="font-semibold">Use additional:</span>{" "}
                      {result.annotations.use_additional}
                    </p>
                  )}
                  {result.annotations.includes &&
                    result.annotations.includes.length > 0 && (
                      <div>
                        <p className="font-semibold text-neutral-700 dark:text-neutral-300">
                          Includes:
                        </p>
                        <ul className="ml-4 list-disc text-neutral-600 dark:text-neutral-400">
                          {result.annotations.includes.map((inc, i) => (
                            <li key={i}>{inc}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
