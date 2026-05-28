import { useQuery } from "@tanstack/react-query";
import { Link, Navigate } from "react-router-dom";

import { PageHeader } from "@/components/layout/PageHeader";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";

/** /review — redirect to the first statement that still has items to review. */
export default function ReviewHub() {
  const pending = useQuery({
    queryKey: ["transactions", "needs_review_hub"],
    queryFn: () =>
      api.transactions.list({ needs_review: true, page_size: 1, page: 1 }),
  });

  if (pending.isLoading) {
    return (
      <div>
        <PageHeader title="Review" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  const first = pending.data?.items[0];
  if (first) {
    return <Navigate to={`/review/${first.statement_id}`} replace />;
  }

  return (
    <div>
      <PageHeader
        title="Review"
        description="No transactions need your input right now."
      />
      <Link to="/upload" className="text-sm text-[--color-accent] hover:underline">
        Back to upload
      </Link>
    </div>
  );
}
