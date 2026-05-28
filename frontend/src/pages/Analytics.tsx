import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { PageHeader } from "@/components/layout/PageHeader";
import { AskSection } from "@/components/analytics/AskSection";
import { CategoryTrendList } from "@/components/analytics/CategoryTrendList";
import { InsightsSection } from "@/components/analytics/InsightsSection";
import { MonthSelector } from "@/components/dashboard/MonthSelector";
import { Skeleton } from "@/components/ui/skeleton";
import { useSelectedMonth } from "@/hooks/useSelectedMonth";
import { api } from "@/lib/api";
import { parseAmount } from "@/lib/currency";

export default function Analytics() {
  const [monthYear, setMonthYear] = useSelectedMonth();

  const dashboard = useQuery({
    queryKey: ["analytics", "dashboard", monthYear.year, monthYear.month],
    queryFn: () => api.analytics.dashboard(monthYear.month, monthYear.year),
  });

  const hasData =
    dashboard.data &&
    (parseAmount(dashboard.data.totals.expense) > 0 ||
      parseAmount(dashboard.data.totals.income) > 0 ||
      dashboard.data.totals.txn_count > 0);

  return (
    <div>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Analytics"
          description="AI insights and questions about your spending."
        />
        <MonthSelector value={monthYear} onChange={setMonthYear} />
      </div>

      {dashboard.isLoading ? (
        <Skeleton className="h-32 w-full" />
      ) : !hasData ? (
        <p className="text-sm text-[--color-text-muted]">
          Upload a statement to see insights.{" "}
          <Link to="/upload" className="text-[--color-accent] hover:underline">
            Go to upload
          </Link>
        </p>
      ) : (
        <>
          <InsightsSection monthYear={monthYear} />
          <AskSection monthYear={monthYear} />
          <section className="mt-12">
            <h2 className="mb-4 text-sm font-medium text-[--color-text-muted]">
              Spending by category
            </h2>
            <CategoryTrendList monthYear={monthYear} />
          </section>
        </>
      )}
    </div>
  );
}
