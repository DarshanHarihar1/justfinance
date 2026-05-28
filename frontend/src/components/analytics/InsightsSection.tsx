import { useMutation } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { useEffect } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { InsightItem } from "@/types/api";
import { formatMonthYear, type MonthYear } from "@/hooks/useSelectedMonth";
import { ApiError, api } from "@/lib/api";

const severityDot: Record<InsightItem["severity"], string> = {
  good: "bg-[--color-success]",
  concern: "bg-[--color-danger]",
  info: "bg-[--color-text-subtle]",
};

export function InsightsSection({ monthYear }: { monthYear: MonthYear }) {
  const { mutate, isPending, data, mutate: regenerate } = useMutation({
    mutationFn: (force: boolean) =>
      api.analytics.insights(
        { month: monthYear.month, year: monthYear.year },
        force,
      ),
    onError: (err) => {
      if (err instanceof ApiError && err.status === 503) {
        toast.error("Insights need an OpenRouter API key on the backend.");
      } else {
        toast.error("Could not generate insights.");
      }
    },
  });

  useEffect(() => {
    mutate(false);
  }, [monthYear.month, monthYear.year, mutate]);

  return (
    <section>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-medium text-[--color-text-muted]">
          Insights — {formatMonthYear(monthYear)}
        </h2>
        <Button
          variant="ghost"
          disabled={isPending}
          onClick={() => regenerate(true)}
        >
          <RefreshCw className="h-4 w-4" strokeWidth={1.5} />
          Regenerate
        </Button>
      </div>

      {isPending && !data ? (
        <div className="space-y-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : data?.insights.length === 0 ? (
        <p className="text-sm text-[--color-text-muted]">
          No spending data for insights this month.
        </p>
      ) : (
        <ul className="space-y-3">
          {data?.insights.map((item, i) => (
            <li
              key={`${item.title}-${i}`}
              className="relative rounded-[--radius-md] border border-[--color-border] bg-[--color-bg-elevated] p-4 pr-8"
            >
              <span
                className={`absolute right-3 top-3 h-2 w-2 rounded-full ${severityDot[item.severity]}`}
                aria-hidden
              />
              <p className="font-medium">{item.title}</p>
              <p className="mt-1 text-sm text-[--color-text-muted]">{item.body}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
