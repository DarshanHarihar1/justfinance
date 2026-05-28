import { Loader2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError, api, apiMessage } from "@/lib/api";

export function ExportSection() {
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [loading, setLoading] = useState(false);

  async function download() {
    setLoading(true);
    try {
      const blob = await api.exportTransactionsCsv({
        from: from || undefined,
        to: to || undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `transactions-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Download started.");
    } catch (err) {
      toast.error(err instanceof ApiError ? apiMessage(err) : "Export failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mt-12">
      <h2 className="mb-4 text-sm font-medium text-[--color-text-muted]">Export</h2>
      <p className="mb-4 text-sm text-[--color-text-muted]">
        Download all transactions as CSV. Leave dates empty for all time.
      </p>
      <div className="mb-4 flex flex-wrap gap-4">
        <label className="text-sm text-[--color-text-muted]">
          From
          <Input
            type="date"
            className="mt-1"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
          />
        </label>
        <label className="text-sm text-[--color-text-muted]">
          To
          <Input
            type="date"
            className="mt-1"
            value={to}
            onChange={(e) => setTo(e.target.value)}
          />
        </label>
      </div>
      <Button onClick={() => void download()} disabled={loading}>
        {loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
        Download all transactions (CSV)
      </Button>
    </section>
  );
}
