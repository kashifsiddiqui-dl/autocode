"use client";

import { FileText, Pill, Stethoscope } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Treatment {
  type: string;
  description: string;
  date?: string;
  provider?: string;
}

interface TreatmentListProps {
  treatments: Treatment[];
  clinicalText?: string;
}

export function TreatmentList({ treatments, clinicalText }: TreatmentListProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Stethoscope className="h-4 w-4 text-primary-600" />
          Treatment Details
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Clinical notes */}
        {clinicalText && (
          <div className="rounded-md bg-neutral-50 p-3 dark:bg-neutral-800">
            <div className="mb-1 flex items-center gap-1.5">
              <FileText className="h-3.5 w-3.5 text-neutral-400" />
              <span className="text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                Clinical Notes
              </span>
            </div>
            <p className="text-sm leading-relaxed text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
              {clinicalText}
            </p>
          </div>
        )}

        {/* Treatment items */}
        {treatments.length > 0 ? (
          <div className="space-y-2">
            {treatments.map((treatment, i) => (
              <div
                key={i}
                className="flex items-start gap-3 rounded-md border border-neutral-100 p-3 dark:border-neutral-800"
              >
                <Pill className="mt-0.5 h-4 w-4 shrink-0 text-primary-500" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-neutral-900 dark:text-white">
                    {treatment.type}
                  </p>
                  <p className="text-sm text-neutral-600 dark:text-neutral-400">
                    {treatment.description}
                  </p>
                  {(treatment.date || treatment.provider) && (
                    <p className="mt-1 text-xs text-neutral-400">
                      {treatment.date && <span>{treatment.date}</span>}
                      {treatment.date && treatment.provider && (
                        <span className="mx-1">-</span>
                      )}
                      {treatment.provider && <span>{treatment.provider}</span>}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          !clinicalText && (
            <p className="py-4 text-center text-sm text-neutral-400">
              No treatment details available.
            </p>
          )
        )}
      </CardContent>
    </Card>
  );
}
