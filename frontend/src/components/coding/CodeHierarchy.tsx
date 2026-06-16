"use client";

import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ChevronDown,
  ChevronRight,
  CircleDot,
  File,
  Folder,
  FolderOpen,
  Search,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type {
  CategoryNode,
  ChapterNode,
  CodeDetail,
  SectionNode,
} from "@/lib/types";

// ---- Tree node types --------------------------------------------------------

type TreeNodeType = "chapter" | "section" | "category" | "code";

interface TreeNodeData {
  type: TreeNodeType;
  id: string;
  label: string;
  codeRange?: string;
  childCount?: number;
  isBillable?: boolean;
}

// ---- Individual tree node ---------------------------------------------------

function TreeNode({
  node,
  depth,
  onSelect,
}: {
  node: TreeNodeData;
  depth: number;
  onSelect: (code: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const isLeaf = node.type === "code";

  // Fetch children based on node type
  const { data: children, isLoading } = useQuery({
    queryKey: ["tree-children", node.type, node.id],
    queryFn: async (): Promise<TreeNodeData[]> => {
      switch (node.type) {
        case "chapter": {
          const sections = await apiClient.getSections(node.id);
          return sections.map((s: SectionNode) => ({
            type: "section" as TreeNodeType,
            id: s.code_range,
            label: s.description,
            codeRange: s.code_range,
            childCount: s.category_count,
          }));
        }
        case "section": {
          const cats = await apiClient.getCodes({ parent: node.id });
          return cats.map((c: CategoryNode) => ({
            type: "category" as TreeNodeType,
            id: c.code,
            label: `${c.code} - ${c.description}`,
            childCount: c.code_count,
            isBillable: c.is_billable,
          }));
        }
        case "category": {
          const codes = await apiClient.getCodes({ parent: node.id });
          return codes.map((c: CategoryNode) => ({
            type: "code" as TreeNodeType,
            id: c.code,
            label: `${c.code} - ${c.description}`,
            isBillable: c.is_billable,
          }));
        }
        default:
          return [];
      }
    },
    enabled: expanded && !isLeaf,
  });

  const handleClick = () => {
    if (isLeaf) {
      onSelect(node.id);
    } else {
      setExpanded(!expanded);
    }
  };

  return (
    <div>
      <button
        onClick={handleClick}
        className={cn(
          "flex w-full items-center gap-1.5 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-neutral-100 dark:hover:bg-neutral-800",
          isLeaf && "cursor-pointer",
        )}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {/* Expand icon */}
        {!isLeaf ? (
          expanded ? (
            <ChevronDown className="h-4 w-4 shrink-0 text-neutral-400" />
          ) : (
            <ChevronRight className="h-4 w-4 shrink-0 text-neutral-400" />
          )
        ) : (
          <span className="w-4" />
        )}

        {/* Node icon */}
        {isLeaf ? (
          <File className="h-4 w-4 shrink-0 text-neutral-400" />
        ) : expanded ? (
          <FolderOpen className="h-4 w-4 shrink-0 text-amber-500" />
        ) : (
          <Folder className="h-4 w-4 shrink-0 text-amber-500" />
        )}

        {/* Label */}
        <span className="min-w-0 flex-1 truncate text-left text-neutral-900 dark:text-white">
          {node.label}
        </span>

        {/* Code range badge */}
        {node.codeRange && (
          <Badge variant="secondary" className="shrink-0 text-[10px]">
            {node.codeRange}
          </Badge>
        )}

        {/* Billable indicator */}
        {node.isBillable && (
          <CircleDot className="h-3 w-3 shrink-0 text-green-500" />
        )}

        {/* Child count */}
        {node.childCount != null && node.childCount > 0 && (
          <span className="shrink-0 text-[10px] text-neutral-400">
            ({node.childCount})
          </span>
        )}
      </button>

      {/* Children */}
      {expanded && (
        <div>
          {isLoading && (
            <div className="space-y-1 py-1" style={{ paddingLeft: `${(depth + 1) * 16 + 8}px` }}>
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-5 w-2/3" />
              <Skeleton className="h-5 w-1/2" />
            </div>
          )}
          {children?.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ---- Main hierarchy component -----------------------------------------------

interface CodeHierarchyProps {
  onSelectCode: (code: string) => void;
  className?: string;
}

export function CodeHierarchy({ onSelectCode, className }: CodeHierarchyProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const { data: chapters, isLoading } = useQuery({
    queryKey: ["chapters"],
    queryFn: apiClient.getChapters,
  });

  const chapterNodes: TreeNodeData[] = (chapters || []).map(
    (ch: ChapterNode) => ({
      type: "chapter" as TreeNodeType,
      id: ch.chapter,
      label: `Chapter ${ch.chapter}: ${ch.description}`,
      codeRange: ch.code_range,
      childCount: ch.section_count,
    }),
  );

  // Filter chapters by search
  const filteredNodes = searchQuery
    ? chapterNodes.filter(
        (n) =>
          n.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
          n.codeRange?.toLowerCase().includes(searchQuery.toLowerCase()),
      )
    : chapterNodes;

  return (
    <div className={cn("flex flex-col", className)}>
      {/* Search */}
      <div className="px-2 pb-3">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-neutral-400" />
          <Input
            placeholder="Filter chapters..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 text-sm"
          />
        </div>
      </div>

      {/* Tree */}
      <ScrollArea className="flex-1">
        <div className="space-y-0.5">
          {isLoading &&
            Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="mx-2 h-7" />
            ))}
          {filteredNodes.map((node) => (
            <TreeNode
              key={node.id}
              node={node}
              depth={0}
              onSelect={onSelectCode}
            />
          ))}
          {!isLoading && filteredNodes.length === 0 && (
            <p className="py-8 text-center text-sm text-neutral-400">
              No chapters match your search.
            </p>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
