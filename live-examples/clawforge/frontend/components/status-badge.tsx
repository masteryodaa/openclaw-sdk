import { Badge } from "@/components/ui/badge";

const STATUS_STYLES: Record<string, string> = {
  created: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
  building: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  completed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  error: "bg-red-500/10 text-red-400 border-red-500/20",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <Badge variant="outline" className={STATUS_STYLES[status] || STATUS_STYLES.created}>
      {status}
    </Badge>
  );
}
