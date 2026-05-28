import { PageHeader } from "@/components/layout/PageHeader";

export function Placeholder({ title, phase }: { title: string; phase: string }) {
  return (
    <div>
      <PageHeader title={title} description={`Available in ${phase}.`} />
      <p className="text-sm text-[--color-text-muted]">
        This section is not built yet. Use Upload and Review for your monthly workflow.
      </p>
    </div>
  );
}
