"use client";

import { useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { ExportFormat, ExportOptions } from "@/lib/types";
import { toast } from "@/components/ui/toast";

const FORMAT_EXTENSIONS: Record<ExportFormat, string> = {
  pdf: ".pdf",
  csv: ".csv",
  json: ".json",
  hl7_fhir: ".fhir.json",
};

const FORMAT_MIME: Record<ExportFormat, string> = {
  pdf: "application/pdf",
  csv: "text/csv",
  json: "application/json",
  hl7_fhir: "application/fhir+json",
};

export function useExport(sessionId: string) {
  const mutation = useMutation({
    mutationFn: async ({
      format,
      options,
    }: {
      format: ExportFormat;
      options?: ExportOptions;
    }) => {
      const blob = await apiClient.downloadExport(sessionId, {
        format,
        options,
      });

      // Trigger browser download
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `coding-session-${sessionId.slice(0, 8)}${FORMAT_EXTENSIONS[format]}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      return { format };
    },
    onSuccess: ({ format }) => {
      toast({
        title: "Export complete",
        description: `Session exported as ${format.toUpperCase()} successfully.`,
        variant: "success",
      });
    },
    onError: (error) => {
      toast({
        title: "Export failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  return {
    exportSession: mutation.mutate,
    isExporting: mutation.isPending,
    error: mutation.error,
  };
}
