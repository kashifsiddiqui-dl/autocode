"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CodingInput } from "@/components/coding/CodingInput";
import { CodingResults } from "@/components/coding/CodingResults";
import { ExportDialog } from "@/components/export/ExportDialog";
import { apiClient } from "@/lib/api";
import { useCodingStore } from "@/stores/coding-store";

export default function CodePage() {
  const [exportOpen, setExportOpen] = useState(false);
  const currentSessionId = useCodingStore((s) => s.currentSessionId);

  // Fetch patients for the selector
  const { data: patientsData } = useQuery({
    queryKey: ["patients"],
    queryFn: () => apiClient.getPatients({ page: "1", per_page: "100" }),
  });

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 lg:px-8">
      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-white">
          Medical Coding
        </h1>
        <p className="mt-1 text-sm text-neutral-500">
          Enter clinical notes to receive AI-powered ICD-10-CM code suggestions.
        </p>
      </div>

      {/* Coding input (the compose area) */}
      <CodingInput patients={patientsData?.items} />

      {/* Results */}
      <div className="mt-6">
        <CodingResults onExport={() => setExportOpen(true)} />
      </div>

      {/* Export dialog */}
      {currentSessionId && (
        <ExportDialog
          sessionId={currentSessionId}
          open={exportOpen}
          onOpenChange={setExportOpen}
        />
      )}
    </div>
  );
}
