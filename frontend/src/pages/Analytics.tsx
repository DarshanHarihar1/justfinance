import { PageHeader } from "@/components/layout/PageHeader";
import { AskSection } from "@/components/analytics/AskSection";
import { CategoryTrendList } from "@/components/analytics/CategoryTrendList";
import { InsightsSection } from "@/components/analytics/InsightsSection";
import { MonthSelector } from "@/components/dashboard/MonthSelector";
import { useSelectedMonth } from "@/hooks/useSelectedMonth";

export default function Analytics() {
  const [monthYear, setMonthYear] = useSelectedMonth();

  return (
    <div>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <PageHeader
          title="Analytics"
          description="AI insights and questions about your spending."
        />
        <MonthSelector value={monthYear} onChange={setMonthYear} />
      </div>

      <InsightsSection monthYear={monthYear} />
      <AskSection monthYear={monthYear} />

      <section className="mt-12">
        <h2 className="mb-4 text-sm font-medium text-[--color-text-muted]">
          Spending by category
        </h2>
        <CategoryTrendList monthYear={monthYear} />
      </section>
    </div>
  );
}
