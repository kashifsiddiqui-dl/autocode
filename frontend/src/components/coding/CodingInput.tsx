"use client";

import { useEffect, useRef } from "react";
import {
  Bot,
  Loader2,
  Send,
  Sparkles,
  UserCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { useCodingStore } from "@/stores/coding-store";
import { useCoding } from "@/hooks/useCoding";
import type { CodingStandard, LLMProvider, Patient } from "@/lib/types";

const MAX_CHARS = 10000;

const standardLabels: Record<CodingStandard, string> = {
  icd10cm: "ICD-10-CM",
  icd10pcs: "ICD-10-PCS",
  cpt: "CPT",
  hcpcs: "HCPCS",
};

interface CodingInputProps {
  patients?: Patient[];
}

export function CodingInput({ patients = [] }: CodingInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const {
    currentInput,
    selectedPatient,
    selectedStandard,
    llmProvider,
    isProcessing,
    setInput,
    setPatient,
    setStandard,
    setProvider,
  } = useCodingStore();
  const { startAnalysis, cancelAnalysis, isLoading } = useCoding();

  const charCount = currentInput.length;
  const wordCount = currentInput.trim()
    ? currentInput.trim().split(/\s+/).length
    : 0;
  const canSubmit = currentInput.trim().length > 0 && !isLoading;

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = "auto";
      ta.style.height = `${Math.max(160, ta.scrollHeight)}px`;
    }
  }, [currentInput]);

  // Auto-save draft
  useEffect(() => {
    const timer = setTimeout(() => {
      if (currentInput) {
        localStorage.setItem("autocode_draft", currentInput);
      }
    }, 1000);
    return () => clearTimeout(timer);
  }, [currentInput]);

  // Load draft on mount
  useEffect(() => {
    const draft = localStorage.getItem("autocode_draft");
    if (draft && !currentInput) {
      setInput(draft);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey) && canSubmit) {
      e.preventDefault();
      startAnalysis();
    }
  };

  return (
    <div
      className={cn(
        "rounded-xl border bg-white shadow-sm transition-all dark:bg-neutral-900",
        isProcessing && "streaming-border border-primary-400",
        !isProcessing && "border-neutral-200 dark:border-neutral-800",
      )}
    >
      {/* Header toolbar */}
      <div className="flex flex-wrap items-center gap-2 border-b border-neutral-100 px-4 py-2.5 dark:border-neutral-800">
        {/* Patient selector */}
        <Select
          value={selectedPatient?.id || "none"}
          onValueChange={(val) => {
            if (val === "none") {
              setPatient(null);
            } else {
              const p = patients.find((p) => p.id === val);
              if (p) setPatient(p);
            }
          }}
        >
          <SelectTrigger className="h-8 w-[200px] text-xs">
            <UserCircle className="mr-1.5 h-3.5 w-3.5 text-neutral-400" />
            <SelectValue placeholder="Select patient (optional)" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">No patient</SelectItem>
            {patients.map((p) => (
              <SelectItem key={p.id} value={p.id}>
                {p.name} ({p.mrn})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Standard selector */}
        <Select
          value={selectedStandard}
          onValueChange={(val) => setStandard(val as CodingStandard)}
        >
          <SelectTrigger className="h-8 w-[140px] text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {(Object.entries(standardLabels) as [CodingStandard, string][]).map(
              ([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ),
            )}
          </SelectContent>
        </Select>

        {/* LLM Provider toggle */}
        <div className="flex items-center rounded-md border border-neutral-200 dark:border-neutral-700">
          <button
            className={cn(
              "flex items-center gap-1 rounded-l-md px-2.5 py-1 text-xs font-medium transition-colors",
              llmProvider === "anthropic"
                ? "bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300"
                : "text-neutral-500 hover:bg-neutral-50 dark:hover:bg-neutral-800",
            )}
            onClick={() => setProvider("anthropic")}
          >
            <Sparkles className="h-3 w-3" />
            Claude
          </button>
          <button
            className={cn(
              "flex items-center gap-1 rounded-r-md px-2.5 py-1 text-xs font-medium transition-colors",
              llmProvider === "openai"
                ? "bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300"
                : "text-neutral-500 hover:bg-neutral-50 dark:hover:bg-neutral-800",
            )}
            onClick={() => setProvider("openai")}
          >
            <Bot className="h-3 w-3" />
            GPT
          </button>
        </div>

        <div className="flex-1" />

        {/* Character/word count */}
        <span
          className={cn(
            "text-xs tabular-nums",
            charCount > MAX_CHARS * 0.9
              ? "text-red-500"
              : "text-neutral-400",
          )}
        >
          {charCount.toLocaleString()} / {MAX_CHARS.toLocaleString()} chars
          {wordCount > 0 && (
            <span className="ml-2 text-neutral-300 dark:text-neutral-600">
              {wordCount} words
            </span>
          )}
        </span>
      </div>

      {/* Text area */}
      <div className="px-4 py-3">
        <textarea
          ref={textareaRef}
          value={currentInput}
          onChange={(e) => {
            if (e.target.value.length <= MAX_CHARS) {
              setInput(e.target.value);
            }
          }}
          onKeyDown={handleKeyDown}
          placeholder="Enter clinical notes, diagnosis, and treatment details...

Example: 56-year-old male presenting with type 2 diabetes mellitus with diabetic chronic kidney disease, stage 3. Patient also has essential hypertension controlled with lisinopril. BMI 32.4, obese."
          className="w-full resize-none border-0 bg-transparent text-sm leading-relaxed text-neutral-900 placeholder:text-neutral-400 focus:outline-none dark:text-white dark:placeholder:text-neutral-500"
          style={{ minHeight: "160px" }}
          disabled={isProcessing}
        />
      </div>

      {/* Footer with submit */}
      <div className="flex items-center justify-between border-t border-neutral-100 px-4 py-2.5 dark:border-neutral-800">
        <p className="text-xs text-neutral-400">
          Press <kbd className="rounded border px-1 py-0.5 text-[10px] font-mono">Ctrl+Enter</kbd> to
          analyze
        </p>

        <div className="flex items-center gap-2">
          {isLoading && (
            <Button variant="ghost" size="sm" onClick={cancelAnalysis}>
              Cancel
            </Button>
          )}
          <Button
            size="sm"
            onClick={startAnalysis}
            disabled={!canSubmit}
            className="gap-2 bg-gradient-to-r from-primary-600 to-clinical-600 text-white hover:from-primary-700 hover:to-clinical-700"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Send className="h-4 w-4" />
                Generate Codes
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
