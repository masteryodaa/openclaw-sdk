"use client";

import Link from "next/link";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { Project } from "@/lib/types";

interface ProjectSidebarProps {
  projects: Project[];
  currentId: string;
  onClose: () => void;
}

export function ProjectSidebar({ projects, currentId, onClose }: ProjectSidebarProps) {
  return (
    <div className="flex w-56 flex-col border-r border-zinc-800 bg-zinc-950">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-800 px-3 py-2">
        <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
          Projects
        </span>
        <button
          onClick={onClose}
          className="rounded p-0.5 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300 text-xs"
          title="Hide sidebar"
        >
          &#10005;
        </button>
      </div>

      {/* Project list */}
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-0.5">
          {projects.length === 0 ? (
            <p className="px-2 py-4 text-xs text-zinc-600 text-center">
              No projects yet
            </p>
          ) : (
            projects.map((p) => (
              <Link
                key={p.id}
                href={`/workspace/${p.id}`}
                className={`flex flex-col gap-0.5 rounded-md px-2.5 py-2 text-left transition-colors ${
                  p.id === currentId
                    ? "bg-emerald-500/10 border border-emerald-500/20"
                    : "hover:bg-zinc-800/60 border border-transparent"
                }`}
              >
                <span
                  className={`text-sm truncate ${
                    p.id === currentId ? "text-emerald-400 font-medium" : "text-zinc-300"
                  }`}
                >
                  {p.name}
                </span>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] rounded px-1 py-0.5 ${
                      p.status === "completed"
                        ? "bg-emerald-500/10 text-emerald-500"
                        : p.status === "error"
                          ? "bg-red-500/10 text-red-400"
                          : p.status === "building"
                            ? "bg-amber-500/10 text-amber-400"
                            : "bg-zinc-800 text-zinc-500"
                    }`}
                  >
                    {p.status}
                  </span>
                  <span className="text-[10px] text-zinc-600">
                    {new Date(p.created_at).toLocaleDateString()}
                  </span>
                </div>
              </Link>
            ))
          )}
        </div>
      </ScrollArea>

      {/* New project link */}
      <div className="border-t border-zinc-800 p-2">
        <Link
          href="/"
          className="flex items-center justify-center gap-1.5 rounded-md border border-zinc-700 px-3 py-1.5 text-xs text-zinc-400 transition-colors hover:border-emerald-500/40 hover:text-emerald-400"
        >
          <span>+</span> New Project
        </Link>
      </div>
    </div>
  );
}
