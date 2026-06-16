"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Check, FolderTree, Plus, Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { CodeHierarchy } from "@/components/coding/CodeHierarchy";
import { apiClient } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { CodeDetail, CodeSearchResult } from "@/lib/types";

export default function BrowsePage() {
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");

  // Debounced search
  const handleSearch = (value: string) => {
    setSearchQuery(value);
    if (value.length >= 2) {
      const timer = setTimeout(() => setDebouncedQuery(value), 300);
      return () => clearTimeout(timer);
    } else {
      setDebouncedQuery("");
    }
  };

  // Search results
  const { data: searchResults, isLoading: isSearching } = useQuery({
    queryKey: ["code-search", debouncedQuery],
    queryFn: () => apiClient.searchCodes(debouncedQuery),
    enabled: debouncedQuery.length >= 2,
  });

  // Code detail
  const { data: codeDetail, isLoading: isLoadingDetail } = useQuery({
    queryKey: ["code-detail", selectedCode],
    queryFn: () => apiClient.getCode(selectedCode!),
    enabled: !!selectedCode,
  });

  return (
    <div className="flex h-full">
      {/* Left panel: tree + search */}
      <div className="flex w-80 shrink-0 flex-col border-r border-neutral-200 dark:border-neutral-800">
        <div className="border-b border-neutral-200 p-4 dark:border-neutral-800">
          <h1 className="flex items-center gap-2 text-lg font-bold text-neutral-900 dark:text-white">
            <FolderTree className="h-5 w-5 text-primary-600" />
            Code Browser
          </h1>
          {/* Search */}
          <div className="relative mt-3">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-neutral-400" />
            <Input
              placeholder="Search codes..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className="pl-8 text-sm"
            />
          </div>
        </div>

        {/* Search results or tree */}
        <ScrollArea className="flex-1">
          {debouncedQuery.length >= 2 ? (
            <div className="p-2">
              <p className="mb-2 px-2 text-xs font-semibold text-neutral-500">
                Search Results
              </p>
              {isSearching && (
                <div className="space-y-2 px-2">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              )}
              {searchResults?.map((result: CodeSearchResult) => (
                <button
                  key={result.code}
                  className={cn(
                    "w-full rounded-md px-2 py-2 text-left transition-colors hover:bg-neutral-100 dark:hover:bg-neutral-800",
                    selectedCode === result.code && "bg-primary-50 dark:bg-primary-950",
                  )}
                  onClick={() => setSelectedCode(result.code)}
                >
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="shrink-0 text-xs">
                      {result.code}
                    </Badge>
                    {result.is_billable && (
                      <span className="h-2 w-2 rounded-full bg-green-500" />
                    )}
                  </div>
                  <p className="mt-0.5 text-xs text-neutral-600 dark:text-neutral-400">
                    {result.description}
                  </p>
                  <p className="mt-0.5 text-[10px] text-neutral-400">
                    {result.hierarchy.chapter_description}
                  </p>
                </button>
              ))}
              {searchResults && searchResults.length === 0 && (
                <p className="py-8 text-center text-sm text-neutral-400">
                  No codes found for &ldquo;{debouncedQuery}&rdquo;
                </p>
              )}
            </div>
          ) : (
            <div className="py-2">
              <CodeHierarchy onSelectCode={setSelectedCode} />
            </div>
          )}
        </ScrollArea>
      </div>

      {/* Right panel: code detail */}
      <div className="flex-1 overflow-y-auto">
        {selectedCode && isLoadingDetail ? (
          <div className="p-6 space-y-4">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-32 w-full" />
          </div>
        ) : codeDetail ? (
          <CodeDetailPanel code={codeDetail} />
        ) : (
          <div className="flex h-full items-center justify-center">
            <div className="text-center">
              <FolderTree className="mx-auto mb-3 h-10 w-10 text-neutral-300" />
              <p className="text-sm text-neutral-500">
                Select a code from the tree or search to view details.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ---- Code detail panel ------------------------------------------------------

function CodeDetailPanel({ code }: { code: CodeDetail }) {
  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <Badge
            variant={code.is_billable ? "success" : "warning"}
            className="text-lg font-bold px-4 py-1"
          >
            {code.code}
          </Badge>
          {code.is_billable ? (
            <Badge variant="success">
              <Check className="mr-0.5 h-3 w-3" /> Billable
            </Badge>
          ) : (
            <Badge variant="warning">Non-billable</Badge>
          )}
        </div>
        <h2 className="mt-3 text-xl font-semibold text-neutral-900 dark:text-white">
          {code.short_description}
        </h2>
        {code.long_description !== code.short_description && (
          <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
            {code.long_description}
          </p>
        )}
      </div>

      {/* Hierarchy */}
      <div className="mb-6 rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
        <h3 className="mb-2 text-sm font-semibold text-neutral-700 dark:text-neutral-300">
          Hierarchy
        </h3>
        <div className="flex flex-wrap items-center gap-1.5 text-sm">
          <Badge variant="outline">Ch. {code.hierarchy.chapter}</Badge>
          <span className="text-neutral-300">/</span>
          <Badge variant="outline">{code.hierarchy.section}</Badge>
          <span className="text-neutral-300">/</span>
          <Badge variant="outline">{code.hierarchy.category}</Badge>
          <span className="text-neutral-300">/</span>
          <Badge variant="default">{code.code}</Badge>
        </div>
        <p className="mt-2 text-xs text-neutral-500">
          {code.hierarchy.chapter_description} &gt;{" "}
          {code.hierarchy.section_description}
          {code.hierarchy.category_description &&
            ` > ${code.hierarchy.category_description}`}
        </p>
      </div>

      {/* Excludes */}
      {code.excludes?.excludes1 && code.excludes.excludes1.length > 0 && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-900 dark:bg-red-950/50">
          <h3 className="text-sm font-semibold text-red-700 dark:text-red-400">
            Excludes1 (Mutually Exclusive)
          </h3>
          <ul className="mt-2 space-y-1 text-sm text-red-600 dark:text-red-400">
            {code.excludes.excludes1.map((ex, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <X className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                {ex}
              </li>
            ))}
          </ul>
        </div>
      )}

      {code.excludes?.excludes2 && code.excludes.excludes2.length > 0 && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/50">
          <h3 className="text-sm font-semibold text-amber-700 dark:text-amber-400">
            Excludes2 (Not Included Here)
          </h3>
          <ul className="mt-2 space-y-1 text-sm text-amber-600 dark:text-amber-400">
            {code.excludes.excludes2.map((ex, i) => (
              <li key={i}>{ex}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Annotations */}
      {code.annotations && (
        <div className="mb-4 rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
          <h3 className="mb-2 text-sm font-semibold text-neutral-700 dark:text-neutral-300">
            Coding Instructions
          </h3>
          {code.annotations.code_first && (
            <p className="text-sm text-neutral-600 dark:text-neutral-400">
              <span className="font-medium">Code first:</span>{" "}
              {code.annotations.code_first}
            </p>
          )}
          {code.annotations.use_additional && (
            <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
              <span className="font-medium">Use additional:</span>{" "}
              {code.annotations.use_additional}
            </p>
          )}
          {code.annotations.includes && code.annotations.includes.length > 0 && (
            <div className="mt-2">
              <p className="font-medium text-sm text-neutral-600 dark:text-neutral-400">
                Includes:
              </p>
              <ul className="ml-4 mt-1 list-disc text-sm text-neutral-500">
                {code.annotations.includes.map((inc, i) => (
                  <li key={i}>{inc}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* 7th character */}
      {code.seventh_character && code.seventh_character.length > 0 && (
        <div className="mb-4 rounded-lg border border-primary-200 bg-primary-50 p-4 dark:border-primary-900 dark:bg-primary-950/50">
          <h3 className="mb-2 text-sm font-semibold text-primary-700 dark:text-primary-300">
            7th Character Extensions
          </h3>
          <div className="space-y-1">
            {code.seventh_character.map((sc) => (
              <div key={sc.character} className="flex items-center gap-2 text-sm">
                <Badge variant="outline" className="font-mono">
                  {sc.character}
                </Badge>
                <span className="text-neutral-600 dark:text-neutral-400">
                  {sc.description}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Related codes */}
      <Separator className="my-4" />
      <div className="grid gap-4 md:grid-cols-2">
        {code.parent_code && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
              Parent Code
            </h4>
            <Badge variant="secondary" className="mt-1">
              {code.parent_code}
            </Badge>
          </div>
        )}
        {code.child_codes && code.child_codes.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
              Child Codes
            </h4>
            <div className="mt-1 flex flex-wrap gap-1">
              {code.child_codes.map((c) => (
                <Badge key={c} variant="secondary">
                  {c}
                </Badge>
              ))}
            </div>
          </div>
        )}
        {code.sibling_codes && code.sibling_codes.length > 0 && (
          <div className="md:col-span-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
              Sibling Codes
            </h4>
            <div className="mt-1 flex flex-wrap gap-1">
              {code.sibling_codes.map((c) => (
                <Badge key={c} variant="outline">
                  {c}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
