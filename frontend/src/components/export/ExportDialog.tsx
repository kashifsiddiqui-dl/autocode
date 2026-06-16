"use client";

import { useState } from "react";
import { Download, FileJson, FileSpreadsheet, FileText, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useExport } from "@/hooks/useExport";
import type { ExportFormat, ExportOptions } from "@/lib/types";

const formats: { value: ExportFormat; label: string; icon: React.ReactNode; description: string }[] = [
  {
    value: "pdf",
    label: "PDF",
    icon: <FileText className="h-5 w-5 text-red-500" />,
    description: "Professional document for medical records",
  },
  {
    value: "csv",
    label: "CSV",
    icon: <FileSpreadsheet className="h-5 w-5 text-green-600" />,
    description: "Spreadsheet-compatible for billing systems",
  },
  {
    value: "json",
    label: "JSON",
    icon: <FileJson className="h-5 w-5 text-amber-500" />,
    description: "Structured data for system integrations",
  },
  {
    value: "hl7_fhir",
    label: "HL7 FHIR",
    icon: <FileJson className="h-5 w-5 text-primary-600" />,
    description: "FHIR R4 Bundle for EMR interoperability",
  },
];

interface ExportDialogProps {
  sessionId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ExportDialog({ sessionId, open, onOpenChange }: ExportDialogProps) {
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>("pdf");
  const [options, setOptions] = useState<ExportOptions>({
    include_rejected: false,
    include_reasoning: true,
    include_confidence: true,
    include_audit_trail: true,
    include_clinical_notes: true,
  });

  const { exportSession, isExporting } = useExport(sessionId);

  const toggleOption = (key: keyof ExportOptions) => {
    setOptions((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleExport = () => {
    exportSession(
      { format: selectedFormat, options },
      { onSuccess: () => onOpenChange(false) },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Export Coding Session</DialogTitle>
          <DialogDescription>
            Choose a format and options for your export.
          </DialogDescription>
        </DialogHeader>

        {/* Format selection */}
        <div className="space-y-2">
          <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
            Format
          </p>
          <div className="grid grid-cols-2 gap-2">
            {formats.map((fmt) => (
              <button
                key={fmt.value}
                className={`flex items-center gap-2 rounded-lg border p-3 text-left transition-colors ${
                  selectedFormat === fmt.value
                    ? "border-primary-500 bg-primary-50 dark:border-primary-400 dark:bg-primary-950"
                    : "border-neutral-200 hover:border-neutral-300 dark:border-neutral-700 dark:hover:border-neutral-600"
                }`}
                onClick={() => setSelectedFormat(fmt.value)}
              >
                {fmt.icon}
                <div>
                  <p className="text-sm font-medium">{fmt.label}</p>
                  <p className="text-[10px] text-neutral-500">{fmt.description}</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Options */}
        <div className="space-y-2">
          <p className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
            Options
          </p>
          <div className="space-y-2">
            {([
              ["include_clinical_notes", "Include clinical notes"],
              ["include_reasoning", "Include AI reasoning"],
              ["include_confidence", "Include confidence scores"],
              ["include_audit_trail", "Include audit trail"],
              ["include_rejected", "Include rejected codes"],
            ] as [keyof ExportOptions, string][]).map(([key, label]) => (
              <label
                key={key}
                className="flex cursor-pointer items-center gap-2 text-sm"
              >
                <input
                  type="checkbox"
                  checked={!!options[key]}
                  onChange={() => toggleOption(key)}
                  className="h-4 w-4 rounded border-neutral-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-neutral-700 dark:text-neutral-300">
                  {label}
                </span>
              </label>
            ))}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleExport} disabled={isExporting}>
            {isExporting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="mr-2 h-4 w-4" />
                Export {selectedFormat.toUpperCase()}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
