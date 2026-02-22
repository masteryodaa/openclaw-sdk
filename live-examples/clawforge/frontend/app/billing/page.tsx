"use client";

import { useEffect, useState } from "react";
import { getBillingSummary } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { BillingSummary } from "@/lib/types";

export default function BillingPage() {
  const [billing, setBilling] = useState<BillingSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getBillingSummary()
      .then(setBilling)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-8">
        <h1 className="text-2xl font-bold mb-6">Billing</h1>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 animate-pulse rounded-lg bg-zinc-800" />
          ))}
        </div>
      </div>
    );
  }

  if (!billing) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-8">
        <h1 className="text-2xl font-bold mb-6">Billing</h1>
        <p className="text-zinc-400">Unable to load billing data.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Billing</h1>

      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 mb-8">
        <Card className="border-zinc-800 bg-zinc-900">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-zinc-400 font-normal">Total Spend</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-emerald-400">
              ${billing.total_cost_usd.toFixed(4)}
            </p>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-900">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-zinc-400 font-normal">Total Tokens</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">
              {billing.total_tokens.toLocaleString()}
            </p>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-900">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-zinc-400 font-normal">Projects</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{billing.project_count}</p>
          </CardContent>
        </Card>
      </div>

      {/* Per-project cost table */}
      <h2 className="text-lg font-semibold mb-4">Cost by Project</h2>
      {billing.projects.length === 0 ? (
        <p className="text-zinc-400 text-sm">No projects yet.</p>
      ) : (
        <div className="rounded-lg border border-zinc-800 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-zinc-800 bg-zinc-900/50">
                <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400 uppercase">Project</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-zinc-400 uppercase">Messages</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-zinc-400 uppercase">Tokens</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-zinc-400 uppercase">Cost</th>
              </tr>
            </thead>
            <tbody>
              {billing.projects.map((p) => (
                <tr key={p.project_id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                  <td className="px-4 py-3 text-sm">{p.project_name}</td>
                  <td className="px-4 py-3 text-right text-sm text-zinc-400">{p.message_count}</td>
                  <td className="px-4 py-3 text-right text-sm text-zinc-400">{p.total_tokens.toLocaleString()}</td>
                  <td className="px-4 py-3 text-right text-sm font-mono text-emerald-400">${p.total_cost_usd.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Cost bar chart (CSS-only) */}
      {billing.projects.length > 0 && (
        <div className="mt-8">
          <h2 className="text-lg font-semibold mb-4">Cost Distribution</h2>
          <div className="space-y-2">
            {billing.projects.map((p) => {
              const maxCost = Math.max(...billing.projects.map((x) => x.total_cost_usd), 0.0001);
              const pct = (p.total_cost_usd / maxCost) * 100;
              return (
                <div key={p.project_id} className="flex items-center gap-3">
                  <span className="w-32 truncate text-sm text-zinc-400">{p.project_name}</span>
                  <div className="flex-1 h-6 rounded bg-zinc-800 overflow-hidden">
                    <div
                      className="h-full rounded bg-emerald-600 transition-all"
                      style={{ width: `${Math.max(pct, 2)}%` }}
                    />
                  </div>
                  <span className="w-20 text-right text-xs font-mono text-zinc-400">
                    ${p.total_cost_usd.toFixed(4)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
