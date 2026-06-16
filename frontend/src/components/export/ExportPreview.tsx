"use client";

import { format } from "date-fns";
import { Check, FileText, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import type { CodingResult, CodingSession, Patient } from "@/lib/types";

interface ExportPreviewProps {
  session: CodingSession;
}

export function ExportPreview({ session }: ExportPreviewProps) {
  const acceptedResults = session.results.filter(
    (r) => r.status === "accepted",
  );
  const now = new Date();

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-6 font-sans text-sm dark:border-neutral-700 dark:bg-neutral-900">
      {/* Header */}
      <div className="mb-4 border-b border-neutral-200 pb-4 dark:border-neutral-700">
        <h2 className="text-lg font-bold text-neutral-900 dark:text-white">
          Medical Coding Report
        </h2>
        <p className="text-xs text-neutral-500">
          Exported on {format(now, "MMMM d, yyyy 'at' h:mm a")}
        </p>
      </div>

      {/* Patient demographics */}
      {session.patient && (
        <div className="mb-4 rounded-md border border-neutral-200 p-3 dark:border-neutral-700">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-neutral-500">
            Patient Demographics
          </h3>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-neutral-500">Name: </span>
              <span className="font-medium text-neutral-900 dark:text-white">
                {session.patient.name}
              </span>
            </div>
            <div>
              <span className="text-neutral-500">MRN: </span>
              <span className="font-medium text-neutral-900 dark:text-white">
                {session.patient.mrn}
              </span>
            </div>
            <div>
              <span className="text-neutral-500">DOB: </span>
              <span className="font-medium text-neutral-900 dark:text-white">
                {session.patient.dob}
              </span>
            </div>
            <div>
              <span className="text-neutral-500">Gender: </span>
              <span className="font-medium capitalize text-neutral-900 dark:text-white">
                {session.patient.gender}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Clinical notes */}
      <div className="mb-4">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-neutral-500">
          Clinical Notes
        </h3>
        <div className="rounded-md bg-neutral-50 p-3 dark:bg-neutral-800">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-neutral-700 dark:text-neutral-300">
            {session.clinical_text}
          </p>
        </div>
      </div>

      <Separator className="my-4" />

      {/* Coding results */}
      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-neutral-500">
          Coding Results ({acceptedResults.length} accepted codes)
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs font-medium text-neutral-500">
                <th className="pb-2 pr-3">Code</th>
                <th className="pb-2 pr-3">Description</th>
                <th className="pb-2 pr-3">Status</th>
                <th className="pb-2 pr-3">Confidence</th>
                <th className="pb-2">Billable</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 dark:divide-neutral-800">
              {session.results.map((result) => (
                <tr
                  key={result.id}
                  className={
                    result.status === "rejected" ? "opacity-50" : ""
                  }
                >
                  <td className="py-2 pr-3">
                    <Badge
                      variant={
                        result.status === "accepted"
                          ? "success"
                          : result.status === "rejected"
                            ? "destructive"
                            : "secondary"
                      }
                      className="text-xs"
                    >
                      {result.code}
                    </Badge>
                  </td>
                  <td className="py-2 pr-3 text-neutral-900 dark:text-white">
                    {result.description}
                  </td>
                  <td className="py-2 pr-3">
                    {result.status === "accepted" ? (
                      <span className="flex items-center gap-1 text-green-600">
                        <Check className="h-3 w-3" /> Accepted
                      </span>
                    ) : result.status === "rejected" ? (
                      <span className="flex items-center gap-1 text-red-500">
                        <X className="h-3 w-3" /> Rejected
                      </span>
                    ) : (
                      <span className="text-neutral-400">Suggested</span>
                    )}
                  </td>
                  <td className="py-2 pr-3 tabular-nums">
                    {(result.confidence * 100).toFixed(0)}%
                  </td>
                  <td className="py-2">
                    {result.is_billable ? (
                      <Check className="h-4 w-4 text-green-500" />
                    ) : (
                      <X className="h-4 w-4 text-neutral-300" />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Footer */}
      <Separator className="my-4" />
      <div className="flex items-center justify-between text-xs text-neutral-400">
        <span>Session ID: {session.id}</span>
        <span>Standard: {session.standard.toUpperCase()}</span>
      </div>
    </div>
  );
}
