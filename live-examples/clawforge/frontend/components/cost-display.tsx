export function CostDisplay({ cost }: { cost: number }) {
  return (
    <span className="inline-flex items-center rounded bg-zinc-800 px-2 py-0.5 text-xs font-mono text-emerald-400">
      ${cost.toFixed(4)}
    </span>
  );
}
