import type { CategoryBreakdown, DashboardTotals } from "@/types/api";
import { formatINR, parseAmount } from "@/lib/currency";

export function SummaryCards({
  totals,
  topCategory,
}: {
  totals: DashboardTotals;
  topCategory: CategoryBreakdown | undefined;
}) {
  const net = parseAmount(totals.net);
  const netNegative = net < 0;

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Card label="Income" value={formatINR(totals.income)} />
      <Card label="Expense" value={formatINR(totals.expense)} />
      <Card
        label="Net"
        value={formatINR(totals.net)}
        className={netNegative ? "text-[--color-danger]" : "text-[--color-success]"}
      />
      <Card
        label="Top category"
        value={topCategory ? formatINR(topCategory.total) : "—"}
        sub={topCategory?.name}
      />
    </div>
  );
}

function Card({
  label,
  value,
  sub,
  className,
}: {
  label: string;
  value: string;
  sub?: string;
  className?: string;
}) {
  return (
    <div className="rounded-[--radius-md] border border-[--color-border] bg-[--color-bg-elevated] px-4 py-3">
      <p className="text-xs font-medium uppercase tracking-wide text-[--color-text-subtle]">
        {label}
      </p>
      <p className={`mt-1 text-xl font-semibold tabular-nums ${className ?? ""}`}>
        {value}
      </p>
      {sub ? (
        <p className="mt-0.5 text-sm text-[--color-text-muted]">{sub}</p>
      ) : null}
    </div>
  );
}
