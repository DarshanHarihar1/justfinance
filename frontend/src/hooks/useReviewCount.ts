import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";

export function useReviewCount() {
  const query = useQuery({
    queryKey: ["transactions", "needs_review_count"],
    queryFn: () =>
      api.transactions.list({ needs_review: true, page_size: 1, page: 1 }),
    refetchInterval: () =>
      document.visibilityState === "visible" ? 60_000 : false,
  });
  return query.data?.total ?? 0;
}
