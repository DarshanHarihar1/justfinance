import { ChevronLeft, ChevronRight } from "lucide-react";

import {
  formatMonthYear,
  shiftMonth,
  type MonthYear,
} from "@/hooks/useSelectedMonth";

export function MonthSelector({
  value,
  onChange,
}: {
  value: MonthYear;
  onChange: (next: MonthYear) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <button
        type="button"
        aria-label="Previous month"
        className="rounded-[--radius-md] border border-[--color-border] p-2 text-[--color-text-muted] transition-colors hover:bg-[--color-bg-muted] hover:text-[--color-text]"
        onClick={() => onChange(shiftMonth(value, -1))}
      >
        <ChevronLeft className="h-4 w-4" strokeWidth={1.5} />
      </button>
      <span className="min-w-[10rem] text-center text-lg font-medium">
        {formatMonthYear(value)}
      </span>
      <button
        type="button"
        aria-label="Next month"
        className="rounded-[--radius-md] border border-[--color-border] p-2 text-[--color-text-muted] transition-colors hover:bg-[--color-bg-muted] hover:text-[--color-text]"
        onClick={() => onChange(shiftMonth(value, 1))}
      >
        <ChevronRight className="h-4 w-4" strokeWidth={1.5} />
      </button>
    </div>
  );
}
