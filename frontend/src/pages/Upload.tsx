import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Dropzone } from "@/components/upload/Dropzone";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, api } from "@/lib/api";
import { formatPeriod, formatRelativeTime } from "@/lib/currency";
import type { ParsedSummary } from "@/types/api";
import { queryClient } from "@/lib/query";

type UploadPhase = "idle" | "uploading" | "done" | "error";

export default function Upload() {
  const navigate = useNavigate();
  const [phase, setPhase] = useState<UploadPhase>("idle");
  const [result, setResult] = useState<ParsedSummary | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    void api.healthz().catch(() => {
      /* cold-start primer — ignore failures */
    });
  }, []);

  const statements = useQuery({
    queryKey: ["statements"],
    queryFn: () => api.statements.list(),
  });

  const upload = useMutation({
    mutationFn: (file: File) => api.statements.upload(file),
    onMutate: () => {
      setPhase("uploading");
      setErrorMessage(null);
      setResult(null);
    },
    onSuccess: (data) => {
      setResult(data);
      setPhase("done");
      void queryClient.invalidateQueries({ queryKey: ["statements"] });
      void queryClient.invalidateQueries({ queryKey: ["transactions"] });
    },
    onError: async (err, file) => {
      if (err instanceof ApiError && (err.status === 502 || err.status === 504)) {
        setErrorMessage("Waking up the backend… this takes about a minute the first time.");
        await new Promise((r) => setTimeout(r, 60_000));
        upload.mutate(file);
        return;
      }
      setPhase("error");
      if (err instanceof ApiError && err.status === 422) {
        setErrorMessage(
          "We couldn't parse this. It looks like it might not be a PhonePe Transaction Statement.",
        );
      } else {
        setErrorMessage("Upload failed. Check your connection and try again.");
      }
    },
  });

  function onFile(file: File) {
    upload.mutate(file);
  }

  function reset() {
    setPhase("idle");
    setResult(null);
    setErrorMessage(null);
  }

  return (
    <div>
      <PageHeader
        title="Upload statement"
        description="Add your monthly PhonePe transaction PDF."
      />

      {phase === "idle" ? <Dropzone onFile={onFile} disabled={upload.isPending} /> : null}
      {phase === "uploading" ? <Dropzone onFile={onFile} disabled compact /> : null}

      {phase === "uploading" ? (
        <p className="mt-4 text-sm text-[--color-text-muted]">
          Parsing PDF and categorizing transactions…
        </p>
      ) : null}

      {phase === "done" && result ? (
        <div className="mt-4 rounded-[--radius-md] border border-[--color-border] bg-[--color-bg-elevated] p-4">
          <p className="text-sm font-medium text-[--color-success]">Done</p>
          <p className="mt-1 text-sm text-[--color-text-muted]">
            Parsed {result.parsed_count} transactions — {result.new_count} new.
          </p>
          {result.warnings.length > 0 ? (
            <ul className="mt-2 text-xs text-[--color-warning]">
              {result.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          ) : null}
          <div className="mt-4 flex flex-wrap gap-2">
            {result.needs_review_count > 0 ? (
              <Button onClick={() => navigate(`/review/${result.statement_id}`)}>
                Review now ({result.needs_review_count})
              </Button>
            ) : (
              <Button variant="secondary" onClick={() => navigate("/dashboard")}>
                View dashboard
              </Button>
            )}
            <Button variant="ghost" onClick={reset}>
              Upload another
            </Button>
          </div>
        </div>
      ) : null}

      {phase === "error" ? (
        <div className="mt-4 rounded-[--radius-md] border border-[--color-border] bg-[--color-bg-elevated] p-4">
          <p className="text-sm text-[--color-danger]">{errorMessage}</p>
          <button
            type="button"
            className="mt-3 text-sm text-[--color-accent] hover:underline"
            onClick={reset}
          >
            Try another file
          </button>
        </div>
      ) : null}

      <section className="mt-12">
        <h2 className="mb-4 text-sm font-medium text-[--color-text-muted]">
          Most recent uploads
        </h2>
        {statements.isLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : statements.isError ? (
          <p className="text-sm text-[--color-danger]">Could not load statements.</p>
        ) : statements.data?.length === 0 ? (
          <p className="text-sm text-[--color-text-muted]">
            Upload your first statement to get started.
          </p>
        ) : (
          <ul className="divide-y divide-[--color-border] border-y border-[--color-border]">
            {statements.data?.map((s) => (
              <li
                key={s.id}
                className="flex items-center justify-between py-3 text-sm"
              >
                <span>{formatPeriod(s.period_start, s.period_end)}</span>
                <span className="text-[--color-text-subtle]">
                  {formatRelativeTime(s.uploaded_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
