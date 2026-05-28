import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { MoMMonth } from "@/types/api";
import { formatINR, parseAmount } from "@/lib/currency";

export function MoMBar({ months }: { months: MoMMonth[] }) {
  const slice = months.slice(-6);
  const chartData = slice.map((m) => ({
    label: m.label.replace(/\s20\d{2}$/, ""),
    income: parseAmount(m.income),
    expense: parseAmount(m.expense),
  }));

  if (chartData.length === 0) return null;

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="var(--color-border)" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: "var(--color-text-subtle)", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "var(--color-text-subtle)", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => formatINR(v).replace("₹", "")}
          />
          <Tooltip
            formatter={(value, name) => {
              const n = typeof value === "number" ? value : Number(value ?? 0);
              const label = name === "income" ? "Income" : "Expense";
              return [formatINR(n), label];
            }}
            contentStyle={{
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
              fontSize: 12,
            }}
          />
          <Bar dataKey="income" fill="var(--color-success)" radius={[2, 2, 0, 0]} />
          <Bar dataKey="expense" fill="var(--color-accent)" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
