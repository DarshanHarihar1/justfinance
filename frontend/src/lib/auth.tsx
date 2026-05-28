import { useQuery } from "@tanstack/react-query";
import { Navigate, Outlet } from "react-router-dom";

import { api } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";

export function AuthGuard() {
  const { isLoading, isError, isSuccess } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: () => api.auth.me(),
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[--color-bg]">
        <div className="w-full max-w-xs space-y-3">
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-10 w-full" />
        </div>
      </div>
    );
  }

  if (isError || !isSuccess) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
