import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { CategoryPicker, saveRecentCategory } from "@/components/transactions/CategoryPicker";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { api } from "@/lib/api";
import { formatDate, formatINRDetailed, formatTime } from "@/lib/currency";
import type { TransactionOut } from "@/types/api";
import { usePrefetchDashboard } from "@/hooks/usePrefetchDashboard";
import { queryClient } from "@/lib/query";

type RowDraft = {
  transactionId: number;
  categoryId: number | null;
  merchantNormalized: string | null;
  muted: boolean;
};

export default function Review() {
  usePrefetchDashboard();
  const { statementId } = useParams<{ statementId: string }>();
  const id = Number(statementId);
  const navigate = useNavigate();
  const [remember, setRemember] = useState(true);
  const [drafts, setDrafts] = useState<RowDraft[]>([]);

  const categories = useQuery({
    queryKey: ["categories"],
    queryFn: () => api.categories.list(),
  });

  const transactions = useQuery({
    queryKey: ["statements", id, "review"],
    queryFn: () => api.statements.review(id),
    enabled: Number.isFinite(id),
  });

  const transfersId = useMemo(
    () => categories.data?.find((c) => c.name === "Transfers")?.id ?? null,
    [categories.data],
  );

  useEffect(() => {
    if (!transactions.data || !categories.data) return;
    setDrafts(
      transactions.data.map((t) => ({
        transactionId: t.id,
        categoryId: t.category_id,
        merchantNormalized: t.merchant_normalized,
        muted: t.category_id === transfersId && transfersId !== null,
      })),
    );
  }, [transactions.data, categories.data, transfersId]);

  const save = useMutation({
    mutationFn: async () => {
      const items = drafts
        .filter((d) => d.categoryId != null)
        .map((d) => ({
          transaction_id: d.transactionId,
          category_id: d.categoryId as number,
          remember,
        }));
      if (items.length === 0) throw new Error("No categories selected");
      await api.transactions.categorize({ items });
    },
    onSuccess: () => {
      toast.success(`${drafts.length} transactions categorized.`);
      void queryClient.invalidateQueries({ queryKey: ["transactions"] });
      void queryClient.invalidateQueries({ queryKey: ["statements"] });
      void queryClient.invalidateQueries({
        queryKey: ["transactions", "needs_review_count"],
      });
      void queryClient.invalidateQueries({
        queryKey: ["transactions", "needs_review_hub"],
      });
      navigate("/upload");
    },
    onError: () => {
      toast.error("Could not save. Try again.");
    },
  });

  function setCategory(txnId: number, categoryId: number) {
    saveRecentCategory(categoryId);
    setDrafts((prev) => {
      const row = prev.find((r) => r.transactionId === txnId);
      const pattern = row?.merchantNormalized;
      return prev.map((r) => {
        if (r.transactionId === txnId) return { ...r, categoryId };
        if (pattern && r.merchantNormalized === pattern) {
          return { ...r, categoryId };
        }
        return r;
      });
    });
  }

  const allSelected = drafts.length > 0 && drafts.every((d) => d.categoryId != null);

  if (!Number.isFinite(id)) {
    return <p className="text-sm text-[--color-danger]">Invalid statement.</p>;
  }

  return (
    <div>
      <div className="mb-6">
        <Link
          to="/upload"
          className="text-sm text-[--color-text-muted] hover:text-[--color-text]"
        >
          ‹ Back to upload
        </Link>
      </div>
      <PageHeader
        title="Review transactions"
        description={
          transactions.data
            ? `${transactions.data.length} transaction${transactions.data.length === 1 ? "" : "s"} to review`
            : undefined
        }
      />

      {transactions.isLoading || categories.isLoading ? (
        <Skeleton className="h-48 w-full" />
      ) : transactions.isError ? (
        <p className="text-sm text-[--color-danger]">Could not load transactions.</p>
      ) : transactions.data?.length === 0 ? (
        <p className="text-sm text-[--color-text-muted]">Nothing left to review.</p>
      ) : (
        <>
          <Table>
            <THead>
              <TR>
                <TH>Date</TH>
                <TH>Description</TH>
                <TH className="text-right">Amount</TH>
                <TH>Category</TH>
              </TR>
            </THead>
            <TBody>
              {transactions.data?.map((txn) => {
                const draft = drafts.find((d) => d.transactionId === txn.id);
                return (
                  <ReviewRow
                    key={txn.id}
                    txn={txn}
                    categories={categories.data ?? []}
                    categoryId={draft?.categoryId ?? null}
                    muted={draft?.muted ?? false}
                    onCategory={(catId) => setCategory(txn.id, catId)}
                  />
                );
              })}
            </TBody>
          </Table>

          <div className="mt-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <label className="flex items-center gap-2 text-sm text-[--color-text-muted]">
              <input
                type="checkbox"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
                className="rounded border-[--color-border-strong]"
              />
              Remember these mappings
            </label>
            <Button
              disabled={!allSelected || save.isPending}
              onClick={() => save.mutate()}
            >
              {save.isPending ? "Saving…" : "Save all"}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}

function ReviewRow({
  txn,
  categories,
  categoryId,
  muted,
  onCategory,
}: {
  txn: TransactionOut;
  categories: import("@/types/api").CategoryOut[];
  categoryId: number | null;
  muted: boolean;
  onCategory: (id: number) => void;
}) {
  return (
    <TR className={muted ? "opacity-60" : undefined}>
      <TD className="whitespace-nowrap text-[--color-text-muted]">
        {formatDate(txn.date)}
        {txn.time ? (
          <div className="text-xs text-[--color-text-subtle]">{formatTime(txn.time)}</div>
        ) : null}
      </TD>
      <TD>
        <div className="font-medium">{txn.description}</div>
        <div className="mt-0.5 font-mono text-xs text-[--color-text-subtle]">
          {txn.transaction_ref}
        </div>
        {txn.type === "credit" ? (
          <div className="text-xs text-[--color-text-muted]">Received</div>
        ) : null}
      </TD>
      <TD className="text-right font-medium tabular-nums">
        {formatINRDetailed(txn.amount)}
      </TD>
      <TD>
        <CategoryPicker
          categories={categories}
          value={categoryId}
          onChange={onCategory}
          compact
        />
      </TD>
    </TR>
  );
}
