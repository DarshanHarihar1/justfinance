import { lazy, Suspense, type ReactNode } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";

import { AuthGuard } from "@/lib/auth";
import { AppShell } from "@/components/layout/AppShell";
import { PageSkeleton } from "@/components/layout/PageSkeleton";
import Login from "@/pages/Login";
import Upload from "@/pages/Upload";
import Review from "@/pages/Review";
import ReviewHub from "@/pages/ReviewHub";

const Dashboard = lazy(() => import("@/pages/Dashboard"));
const Analytics = lazy(() => import("@/pages/Analytics"));
const Settings = lazy(() => import("@/pages/Settings"));

function Lazy({ children }: { children: ReactNode }) {
  return <Suspense fallback={<PageSkeleton />}>{children}</Suspense>;
}

export const router = createBrowserRouter([
  { path: "/login", element: <Login /> },
  {
    element: <AuthGuard />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: "/", element: <Navigate to="/upload" replace /> },
          { path: "/upload", element: <Upload /> },
          { path: "/review", element: <ReviewHub /> },
          { path: "/review/:statementId", element: <Review /> },
          {
            path: "/dashboard",
            element: (
              <Lazy>
                <Dashboard />
              </Lazy>
            ),
          },
          {
            path: "/analytics",
            element: (
              <Lazy>
                <Analytics />
              </Lazy>
            ),
          },
          {
            path: "/settings",
            element: (
              <Lazy>
                <Settings />
              </Lazy>
            ),
          },
        ],
      },
    ],
  },
]);
