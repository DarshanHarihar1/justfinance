import { Outlet } from "react-router-dom";

import { NavRail } from "@/components/layout/NavRail";

export function AppShell() {
  return (
    <div className="flex min-h-screen bg-[--color-bg]">
      <NavRail />
      <main className="min-w-0 flex-1 px-6 py-8 md:px-10">
        <div className="mx-auto max-w-4xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
