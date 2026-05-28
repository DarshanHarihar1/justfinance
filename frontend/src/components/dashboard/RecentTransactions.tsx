import { Link } from "react-router-dom";

import type { TransactionOut } from "@/types/api";
import { formatDate, formatINRDetailed } from "@/lib/currency";

export function RecentTransactions({ items }: { items: TransactionOut[] }) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-[--color-text-muted]">No transactions this month.</p>
    );
  }

  return (
    <ul className="divide-y divide-[--color-border] border-y border-[--color-border]">
      {items.map((txn) => (
        <li key={txn.id} className="flex items-center justify-between gap-4 py-3 text-sm">
          <div className="min-w-0">
            <p className="truncate font-medium">{txn.description}</p>
            <p className="text-xs text-[--color-text-subtle]">
              {formatDate(txn.date)}
              {txn.needs_review ? (
                <span className="ml-2 text-[--color-warning]">needs review</span>
              ) : null}
            </p>
          </div>
          <span className="shrink-0 tabular-nums font-medium">
            {formatINRDetailed(txn.amount)}
          </span>
        </li>
      ))}
    </ul>
  );
}

export function ReviewBanner({ count }: { count: number }) {
  if (count <= 0) return null;
  return (
    <div className="mb-6 flex flex-wrap items-center justify-between gap-2 rounded-[--radius-md] border border-[--color-border] bg-[--color-accent-soft] px-4 py-3 text-sm">
      <span>
        {count} transaction{count === 1 ? "" : "s"} need review this month.
      </span>
      <Link to="/review" className="font-medium text-[--color-accent] hover:underline">
        Review them →
      </Link>
    </div>
  );
}
