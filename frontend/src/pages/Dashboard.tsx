import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { CategoryDonut } from "@/components/dashboard/CategoryDonut";
import { MoMBar } from "@/components/dashboard/MoMBar";
import { MonthSelector } from "@/components/dashboard/MonthSelector";
import {
  RecentTransactions,
  ReviewBanner,
} from "@/components/dashboard/RecentTransactions";
import { SummaryCards } from "@/components/dashboard/SummaryCards";
import { PageHeader } from "@/components/layout/PageHeader";
import { Skeleton } from "@/components/ui/skeleton";
import { useSelectedMonth } from "@/hooks/useSelectedMonth";
import { api } from "@/lib/api";
import { parseAmount } from "@/lib/currency";

export default function Dashboard() {
  const [monthYear, setMonthYear] = useSelectedMonth();

  const dashboard = useQuery({
    queryKey: ["analytics", "dashboard", monthYear.year, monthYear.month],
    queryFn: () => api.analytics.dashboard(monthYear.month, monthYear.year),
  });

  const mom = useQuery({
    queryKey: ["analytics", "mom"],
    queryFn: () => api.analytics.mom(),
  });

  const isEmpty =
    dashboard.data &&
    parseAmount(dashboard.data.totals.expense) === 0 &&
    parseAmount(dashboard.data.totals.income) === 0 &&
    dashboard.data.totals.txn_count === 0;

  return (
    <div>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader title="Dashboard" description="Monthly income, spending, and trends." />
        <MonthSelector value={monthYear} onChange={setMonthYear} />
      </div>

      {dashboard.isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : dashboard.isError ? (
        <p className="text-sm text-[--color-danger]">Could not load dashboard.</p>
      ) : isEmpty ? (
        <div className="rounded-[--radius-lg] border border-[--color-border] bg-[--color-bg-elevated] px-6 py-12 text-center">
          <p className="text-sm text-[--color-text-muted]">
            No data for this month yet. Upload a statement to get started.
          </p>
          <Link
            to="/upload"
            className="mt-4 inline-flex items-center justify-center rounded-[--radius-md] bg-[--color-accent] px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            Go to upload
          </Link>
        </div>
      ) : dashboard.data ? (
        <>
          <ReviewBanner count={dashboard.data.needs_review_count} />
          <SummaryCards
            totals={dashboard.data.totals}
            topCategory={dashboard.data.by_category[0]}
          />

          <div className="mt-10 grid gap-10 lg:grid-cols-2">
            <section>
              <h2 className="mb-4 text-sm font-medium text-[--color-text-muted]">
                Spending by category
              </h2>
              <CategoryDonut data={dashboard.data.by_category} />
            </section>
            <section>
              <h2 className="mb-4 text-sm font-medium text-[--color-text-muted]">
                Last 6 months
              </h2>
              {mom.isLoading ? (
                <Skeleton className="h-64 w-full" />
              ) : mom.data ? (
                <MoMBar months={mom.data.months} />
              ) : null}
            </section>
          </div>

          <section className="mt-10">
            <h2 className="mb-4 text-sm font-medium text-[--color-text-muted]">
              Recent transactions
            </h2>
            <RecentTransactions items={dashboard.data.recent_transactions} />
          </section>
        </>
      ) : null}
    </div>
  );
}
