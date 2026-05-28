import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import type { CategoryBreakdown } from "@/types/api";
import { formatINR, parseAmount } from "@/lib/currency";

export function CategoryDonut({ data }: { data: CategoryBreakdown[] }) {
  if (data.length === 0) {
    return (
      <p className="text-sm text-[--color-text-muted]">No spending this month.</p>
    );
  }

  const chartData = data.map((c) => ({
    name: c.name,
    value: parseAmount(c.total),
    color: c.color,
    txn_count: c.txn_count,
    pct: c.pct_of_expense,
  }));

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius="60%"
            outerRadius="85%"
            paddingAngle={1}
            stroke="var(--color-border)"
            strokeWidth={1}
          >
            {chartData.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.[0]) return null;
              const row = payload[0].payload as (typeof chartData)[0];
              return (
                <div className="rounded-[--radius-sm] border border-[--color-border] bg-[--color-bg-elevated] px-3 py-2 text-sm shadow-sm">
                  <p className="font-medium">{row.name}</p>
                  <p className="text-[--color-text-muted]">
                    {formatINR(row.value)} · {row.txn_count} txns ·{" "}
                    {Math.round(row.pct * 100)}%
                  </p>
                </div>
              );
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
