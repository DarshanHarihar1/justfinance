import { useMemo } from "react";
import { useSearchParams } from "react-router-dom";

export type MonthYear = { month: number; year: number };

function currentMonthYear(): MonthYear {
  const now = new Date();
  return { month: now.getMonth() + 1, year: now.getFullYear() };
}

export function useSelectedMonth(): [MonthYear, (next: MonthYear) => void] {
  const [params, setParams] = useSearchParams();
  const selected = useMemo(() => {
    const month = Number(params.get("month"));
    const year = Number(params.get("year"));
    if (month >= 1 && month <= 12 && year >= 2000) {
      return { month, year };
    }
    return currentMonthYear();
  }, [params]);

  function setSelected(next: MonthYear) {
    setParams(
      { month: String(next.month), year: String(next.year) },
      { replace: true },
    );
  }

  return [selected, setSelected];
}

export function shiftMonth(
  { month, year }: MonthYear,
  delta: number,
): MonthYear {
  let m = month + delta;
  let y = year;
  while (m < 1) {
    m += 12;
    y -= 1;
  }
  while (m > 12) {
    m -= 12;
    y += 1;
  }
  return { month: m, year: y };
}

export function formatMonthYear({ month, year }: MonthYear): string {
  return new Date(year, month - 1, 1).toLocaleDateString("en-IN", {
    month: "long",
    year: "numeric",
  });
}
