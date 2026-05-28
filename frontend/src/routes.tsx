import { createBrowserRouter, Navigate } from "react-router-dom";

import { AuthGuard } from "@/lib/auth";
import { AppShell } from "@/components/layout/AppShell";
import Login from "@/pages/Login";
import Upload from "@/pages/Upload";
import Review from "@/pages/Review";
import ReviewHub from "@/pages/ReviewHub";
import Dashboard from "@/pages/Dashboard";
import Analytics from "@/pages/Analytics";
import { Placeholder } from "@/pages/Placeholder";

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
          { path: "/dashboard", element: <Dashboard /> },
          { path: "/analytics", element: <Analytics /> },
          {
            path: "/settings",
            element: <Placeholder title="Settings" phase="Phase 8" />,
          },
        ],
      },
    ],
  },
]);
