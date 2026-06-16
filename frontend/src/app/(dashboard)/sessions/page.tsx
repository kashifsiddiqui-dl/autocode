"use client";

import { useState } from "react";
import Link from "next/link";
import { formatDistanceToNow, format } from "date-fns";
import {
  Calendar,
  ChevronLeft,
  ChevronRight,
  Clock,
  FileText,
  Filter,
  Search,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useSessions, useDeleteSession } from "@/hooks/useSession";
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

export default function SessionsPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const { sessions, total, totalPages, isLoading } = useSessions({
    page,
    perPage: 20,
    status: statusFilter === "all" ? undefined : (statusFilter as SessionStatus),
  });

  const deleteMutation = useDeleteSession();

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 lg:px-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-white">
          Session History
        </h1>
        <p className="mt-1 text-sm text-neutral-500">
          View and manage your past coding sessions.
        </p>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[160px]">
            <Filter className="mr-2 h-4 w-4 text-neutral-400" />
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="in_review">In Review</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
          </SelectContent>
        </Select>

        <div className="flex-1" />

        <span className="text-sm text-neutral-500">
          {total} session{total !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Sessions list */}
      <div className="space-y-2">
        {isLoading &&
          Array.from({ length: 5 }).map((_, i) => (
            <div
              key={i}
              className="rounded-lg border border-neutral-200 bg-white p-4 dark:border-neutral-800 dark:bg-neutral-900"
            >
              <div className="flex items-center gap-4">
                <Skeleton className="h-5 w-24" />
                <Skeleton className="h-4 w-48" />
                <div className="flex-1" />
                <Skeleton className="h-5 w-16" />
              </div>
            </div>
          ))}

        {sessions.map((session) => (
          <Link
            key={session.id}
            href={`/sessions/${session.id}`}
            className="block rounded-lg border border-neutral-200 bg-white p-4 transition-colors hover:border-primary-200 hover:bg-primary-50/30 dark:border-neutral-800 dark:bg-neutral-900 dark:hover:border-primary-900 dark:hover:bg-primary-950/20"
          >
            <div className="flex items-center gap-4">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="truncate text-sm font-medium text-neutral-900 dark:text-white">
                    {session.patient_name || "Unnamed Session"}
                  </p>
                  <Badge variant={statusVariant[session.status]}>
                    {statusLabel[session.status]}
                  </Badge>
                </div>
                <div className="mt-1 flex items-center gap-4 text-xs text-neutral-500">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {formatDistanceToNow(new Date(session.created_at), {
                      addSuffix: true,
                    })}
                  </span>
                  <span className="flex items-center gap-1">
                    <FileText className="h-3 w-3" />
                    {session.code_count} codes
                  </span>
                  <span className="uppercase">
                    {session.standard}
                  </span>
                </div>
              </div>

              <Button
                variant="ghost"
                size="icon"
                className="shrink-0 text-neutral-400 hover:text-red-500"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  if (confirm("Delete this session?")) {
                    deleteMutation.mutate(session.id);
                  }
                }}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </Link>
        ))}

        {!isLoading && sessions.length === 0 && (
          <div className="py-16 text-center">
            <FileText className="mx-auto mb-3 h-10 w-10 text-neutral-300" />
            <p className="text-sm text-neutral-500">No sessions found.</p>
            <Link href="/code">
              <Button variant="link" className="mt-2">
                Start a new coding session
              </Button>
            </Link>
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-6 flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </Button>
          <span className="text-sm text-neutral-500">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  );
}
