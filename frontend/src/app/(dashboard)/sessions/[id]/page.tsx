"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Check, Download, Loader2, X } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PatientHeader } from "@/components/patient/PatientHeader";
import { TreatmentList } from "@/components/patient/TreatmentList";
import { CodeCard } from "@/components/coding/CodeCard";
import { ExportDialog } from "@/components/export/ExportDialog";
import { ExportPreview } from "@/components/export/ExportPreview";
import { useSession, useUpdateResultStatus } from "@/hooks/useSession";
import type { SessionStatus } from "@/lib/types";

const statusVariant: Record<SessionStatus, "default" | "warning" | "success"> = {
  draft: "warning",
  in_review: "default",
  completed: "success",
};

const statusLabel: Record<SessionStatus, string> = {
  draft: "Draft",
  in_review: "In Review",
  completed: "Completed",
};

export default function SessionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const [exportOpen, setExportOpen] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  const { session, isLoading, error } = useSession(id);
  const updateResult = useUpdateResultStatus(id);

  if (isLoading) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-6 lg:px-8">
        <Skeleton className="mb-4 h-8 w-64" />
        <Skeleton className="mb-6 h-4 w-48" />
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-6 lg:px-8">
        <p className="text-red-500">Failed to load session.</p>
        <Button variant="outline" className="mt-2" onClick={() => router.back()}>
          Go back
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 lg:px-8">
      {/* Header */}
      <div className="mb-6">
        <Button
          variant="ghost"
          size="sm"
          className="mb-2 -ml-2"
          onClick={() => router.back()}
        >
          <ArrowLeft className="mr-1 h-4 w-4" />
          Back
        </Button>

        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-neutral-900 dark:text-white">
                {session.patient?.name || "Coding Session"}
              </h1>
              <Badge variant={statusVariant[session.status]}>
                {statusLabel[session.status]}
              </Badge>
            </div>
            <p className="mt-1 text-sm text-neutral-500">
              {formatDistanceToNow(new Date(session.created_at), {
                addSuffix: true,
              })}{" "}
              - {session.results.length} codes - {session.standard.toUpperCase()}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowPreview(!showPreview)}
            >
              {showPreview ? "Hide Preview" : "Preview"}
            </Button>
            <Button size="sm" onClick={() => setExportOpen(true)}>
              <Download className="mr-1.5 h-4 w-4" />
              Export
            </Button>
          </div>
        </div>
      </div>

      {/* Patient info */}
      {session.patient && (
        <div className="mb-4">
          <PatientHeader patient={session.patient} />
        </div>
      )}

      {/* Clinical notes */}
      <div className="mb-6">
        <TreatmentList treatments={[]} clinicalText={session.clinical_text} />
      </div>

      {/* Export preview */}
      {showPreview && (
        <div className="mb-6">
          <h2 className="mb-3 text-lg font-semibold text-neutral-900 dark:text-white">
            Export Preview
          </h2>
          <ExportPreview session={session} />
        </div>
      )}

      {/* Code results */}
      <h2 className="mb-3 text-lg font-semibold text-neutral-900 dark:text-white">
        Coding Results ({session.results.length})
      </h2>
      <div className="space-y-3">
        {session.results.map((result) => (
          <CodeCard
            key={result.id}
            result={result}
            onAccept={() =>
              updateResult.mutate({ resultId: result.id, status: "accepted" })
            }
            onReject={() =>
              updateResult.mutate({ resultId: result.id, status: "rejected" })
            }
          />
        ))}
      </div>

      {/* Export dialog */}
      <ExportDialog
        sessionId={id}
        open={exportOpen}
        onOpenChange={setExportOpen}
      />
    </div>
  );
}
