"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Clock, FileText, Plus } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { apiClient } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { SessionStatus } from "@/lib/types";

const statusVariant: Record<SessionStatus, "default" | "warning" | "success"> =
  {
    draft: "warning",
    in_review: "default",
    completed: "success",
  };

const statusLabel: Record<SessionStatus, string> = {
  draft: "Draft",
  in_review: "In Review",
  completed: "Completed",
};

export function Sidebar() {
  const { data, isLoading } = useQuery({
    queryKey: ["recent-sessions"],
    queryFn: () =>
      apiClient.getSessions({ page: "1", per_page: "10" }),
  });

  return (
    <aside className="hidden w-64 shrink-0 border-r bg-neutral-50 dark:bg-neutral-900 lg:block">
      <div className="flex h-full flex-col">
        {/* Quick actions */}
        <div className="p-4">
          <Link href="/code">
            <Button className="w-full gap-2" size="sm">
              <Plus className="h-4 w-4" />
              New Coding Session
            </Button>
          </Link>
        </div>

        <Separator />

        {/* Recent sessions */}
        <div className="px-4 pt-4 pb-2">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
            Recent Sessions
          </h3>
        </div>

        <ScrollArea className="flex-1 px-2">
          <div className="space-y-1 p-2">
            {isLoading &&
              Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="space-y-2 rounded-md p-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              ))}

            {data?.items.map((session) => (
              <Link
                key={session.id}
                href={`/sessions/${session.id}`}
                className="block rounded-md p-2 transition-colors hover:bg-neutral-100 dark:hover:bg-neutral-800"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-neutral-900 dark:text-white">
                      {session.patient_name || "Unnamed Session"}
                    </p>
                    <div className="mt-1 flex items-center gap-2 text-xs text-neutral-500">
                      <Clock className="h-3 w-3" />
                      {formatDistanceToNow(new Date(session.created_at), {
                        addSuffix: true,
                      })}
                    </div>
                  </div>
                  <Badge variant={statusVariant[session.status]} className="shrink-0">
                    {statusLabel[session.status]}
                  </Badge>
                </div>
                <div className="mt-1 flex items-center gap-1 text-xs text-neutral-400">
                  <FileText className="h-3 w-3" />
                  {session.code_count} codes
                </div>
              </Link>
            ))}

            {data && data.items.length === 0 && (
              <p className="py-8 text-center text-sm text-neutral-400">
                No sessions yet. Start coding!
              </p>
            )}
          </div>
        </ScrollArea>
      </div>
    </aside>
  );
}
