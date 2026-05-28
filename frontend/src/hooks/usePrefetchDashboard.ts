import { useEffect } from "react";

import { api } from "@/lib/api";
import { queryClient } from "@/lib/query";

function currentMonthYear() {
  const now = new Date();
  return { month: now.getMonth() + 1, year: now.getFullYear() };
}

/** Prime dashboard data so /dashboard feels instant after upload/review. */
export function usePrefetchDashboard() {
  useEffect(() => {
    const { month, year } = currentMonthYear();
    void queryClient.prefetchQuery({
      queryKey: ["analytics", "dashboard", year, month],
      queryFn: () => api.analytics.dashboard(month, year),
    });
    void queryClient.prefetchQuery({
      queryKey: ["analytics", "mom"],
      queryFn: () => api.analytics.mom(),
    });
  }, []);
}
