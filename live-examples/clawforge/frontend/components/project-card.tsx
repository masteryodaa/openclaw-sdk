import Link from "next/link";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Project } from "@/lib/types";

function statusColor(status: string) {
  switch (status) {
    case "completed": return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
    case "building": return "bg-amber-500/10 text-amber-400 border-amber-500/20";
    case "error": return "bg-red-500/10 text-red-400 border-red-500/20";
    default: return "bg-zinc-500/10 text-zinc-400 border-zinc-500/20";
  }
}

export function ProjectCard({ project }: { project: Project }) {
  const date = new Date(project.created_at).toLocaleDateString();

  return (
    <Link href={`/workspace/${project.id}`}>
      <Card className="border-zinc-800 bg-zinc-900 transition-colors hover:border-zinc-700 hover:bg-zinc-800/80 cursor-pointer">
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between">
            <CardTitle className="text-base font-medium line-clamp-1">
              {project.name}
            </CardTitle>
            <Badge variant="outline" className={statusColor(project.status)}>
              {project.status}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="pb-2">
          <p className="text-sm text-zinc-400 line-clamp-2">{project.description}</p>
        </CardContent>
        <CardFooter className="text-xs text-zinc-500 flex justify-between">
          <span>{date}</span>
          <span>${project.total_cost_usd.toFixed(4)}</span>
        </CardFooter>
      </Card>
    </Link>
  );
}
