"use client";

/**
 * UsagePanel.tsx — Aggregated token-spending & system stats.
 *
 * Displays totals fetched from the backend ``/stats`` endpoint:
 * tokens spent (in/out), queries answered, average latency,
 * document count, and vectors stored.
 */

import React from "react";
import type { UsageStats } from "@/lib/api";

interface UsagePanelProps {
  stats: UsageStats | null;
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

export default function UsagePanel({ stats }: UsagePanelProps) {
  if (!stats) {
    return (
      <div className="border-t border-slate-800 px-4 py-3">
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Usage
        </h2>
        <p className="text-[11px] text-slate-600">Loading stats…</p>
      </div>
    );
  }

  const rows: { label: string; value: string; hint?: string }[] = [
    {
      label: "Tokens spent",
      value: formatTokens(stats.total_tokens),
      hint: `${formatTokens(stats.total_prompt_tokens)} in · ${formatTokens(
        stats.total_completion_tokens,
      )} out`,
    },
    {
      label: "Queries",
      value: stats.total_queries.toLocaleString(),
      hint:
        stats.avg_latency_ms > 0
          ? `avg ${(stats.avg_latency_ms / 1000).toFixed(1)}s`
          : undefined,
    },
    {
      label: "Docs / chunks",
      value: `${stats.documents} / ${stats.vectors_stored.toLocaleString()}`,
    },
  ];

  return (
    <div className="border-t border-slate-800 px-4 py-3">
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
        Usage
      </h2>
      <dl className="flex flex-col gap-2">
        {rows.map((row) => (
          <div key={row.label} className="flex items-baseline justify-between">
            <dt className="text-[11px] text-slate-500">
              {row.label}
              {row.hint && (
                <span className="ml-1.5 text-[10px] text-slate-600">
                  {row.hint}
                </span>
              )}
            </dt>
            <dd className="text-xs font-semibold text-indigo-300">
              {row.value}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
