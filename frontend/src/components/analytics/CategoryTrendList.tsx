import { useQueries, useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import type { MonthYear } from "@/hooks/useSelectedMonth";
import { api } from "@/lib/api";
import { formatINR, parseAmount } from "@/lib/currency";
import { cn } from "@/lib/cn";

function Sparkline({ values }: { values: number[] }) {
  if (values.length === 0) return null;
  const max = Math.max(...values, 1);
  return (
    <div className="flex h-6 items-end gap-px" aria-hidden>
      {values.map((v, i) => (
        <div
          key={i}
          className="w-1 rounded-sm bg-[--color-accent]"
          style={{ height: `${Math.max(8, (v / max) * 100)}%`, opacity: 0.35 + (v / max) * 0.65 }}
        />
      ))}
    </div>
  );
}

export function CategoryTrendList({ monthYear }: { monthYear: MonthYear }) {
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const dashboard = useQuery({
    queryKey: ["analytics", "dashboard", monthYear.year, monthYear.month],
    queryFn: () => api.analytics.dashboard(monthYear.month, monthYear.year),
  });

  const categories = dashboard.data?.by_category ?? [];

  const trends = useQueries({
    queries: categories.map((c) => ({
      queryKey: ["analytics", "trends", c.category_id],
      queryFn: () => api.analytics.trends(c.category_id),
      staleTime: 60_000,
    })),
  });

  if (dashboard.isLoading) {
    return <Skeleton className="h-32 w-full" />;
  }

  if (categories.length === 0) {
    return (
      <p className="text-sm text-[--color-text-muted]">No categorized spending yet.</p>
    );
  }

  return (
    <ul className="divide-y divide-[--color-border] border-y border-[--color-border]">
      {categories.map((cat, idx) => {
        const trend = trends[idx]?.data;
        const points = trend?.months.map((m) => parseAmount(m.total)) ?? [];
        const last = points[points.length - 1] ?? 0;
        const prev = points[points.length - 2] ?? 0;
        const delta = prev > 0 ? ((last - prev) / prev) * 100 : 0;
        const expanded = expandedId === cat.category_id;

        return (
          <li key={cat.category_id}>
            <button
              type="button"
              className="flex w-full items-center gap-4 py-3 text-left text-sm hover:bg-[--color-bg-muted]"
              onClick={() =>
                setExpandedId(expanded ? null : cat.category_id)
              }
            >
              <span
                className="h-2 w-2 shrink-0 rounded-full"
                style={{ backgroundColor: cat.color }}
              />
              <span className="min-w-[8rem] flex-1 font-medium">{cat.name}</span>
              <span className="tabular-nums">{formatINR(cat.total)}</span>
              <Sparkline values={points} />
              <span
                className={cn(
                  "w-14 text-right text-xs tabular-nums",
                  delta >= 0 ? "text-[--color-danger]" : "text-[--color-success]",
                )}
              >
                {delta >= 0 ? "↑" : "↓"} {Math.abs(Math.round(delta))}%
              </span>
            </button>
            {expanded && trend && trend.top_merchants.length > 0 ? (
              <ul className="border-t border-[--color-border] bg-[--color-bg-muted] px-4 py-2 text-xs text-[--color-text-muted]">
                {trend.top_merchants.slice(0, 5).map((m) => (
                  <li key={m.merchant_normalized} className="flex justify-between py-1">
                    <span>{m.merchant_normalized}</span>
                    <span className="tabular-nums">{formatINR(m.total)}</span>
                  </li>
                ))}
              </ul>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}
