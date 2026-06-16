"use client";

import { Calendar, Hash, User } from "lucide-react";
import { format, parseISO } from "date-fns";
import type { Patient } from "@/lib/types";

interface PatientHeaderProps {
  patient: Patient;
  compact?: boolean;
}

export function PatientHeader({ patient, compact = false }: PatientHeaderProps) {
  const formattedDob = patient.dob
    ? format(parseISO(patient.dob), "MMM d, yyyy")
    : "N/A";

  if (compact) {
    return (
      <div className="flex items-center gap-4 text-sm">
        <span className="font-medium text-neutral-900 dark:text-white">
          {patient.name}
        </span>
        <span className="text-neutral-500">MRN: {patient.mrn}</span>
        <span className="text-neutral-500">DOB: {formattedDob}</span>
        <span className="text-neutral-500 capitalize">{patient.gender}</span>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900">
      <h3 className="mb-3 text-sm font-semibold text-neutral-900 dark:text-white">
        Patient Information
      </h3>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div className="flex items-center gap-2">
          <User className="h-4 w-4 text-neutral-400" />
          <div>
            <p className="text-[10px] uppercase tracking-wider text-neutral-400">
              Name
            </p>
            <p className="text-sm font-medium text-neutral-900 dark:text-white">
              {patient.name}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Hash className="h-4 w-4 text-neutral-400" />
          <div>
            <p className="text-[10px] uppercase tracking-wider text-neutral-400">
              MRN
            </p>
            <p className="text-sm font-medium text-neutral-900 dark:text-white">
              {patient.mrn}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-neutral-400" />
          <div>
            <p className="text-[10px] uppercase tracking-wider text-neutral-400">
              Date of Birth
            </p>
            <p className="text-sm font-medium text-neutral-900 dark:text-white">
              {formattedDob}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <User className="h-4 w-4 text-neutral-400" />
          <div>
            <p className="text-[10px] uppercase tracking-wider text-neutral-400">
              Gender
            </p>
            <p className="text-sm font-medium capitalize text-neutral-900 dark:text-white">
              {patient.gender}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
