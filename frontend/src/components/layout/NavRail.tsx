import {
  LayoutDashboard,
  LineChart,
  ListTodo,
  LogOut,
  Settings,
  Upload,
} from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { api } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useReviewCount } from "@/hooks/useReviewCount";
import { queryClient } from "@/lib/query";

const navClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    "flex flex-col items-center gap-1 rounded-[--radius-md] px-2 py-2 text-[10px] text-[--color-text-muted] transition-colors duration-150 md:flex-row md:gap-2 md:px-3 md:text-xs",
    isActive
      ? "bg-[--color-accent-soft] text-[--color-accent]"
      : "hover:bg-[--color-bg-muted] hover:text-[--color-text]",
  );

export function NavRail() {
  const navigate = useNavigate();
  const reviewCount = useReviewCount();

  async function logout() {
    try {
      await api.auth.logout();
      queryClient.clear();
      navigate("/login", { replace: true });
    } catch {
      toast.error("Could not log out. Try again.");
    }
  }

  return (
    <nav className="flex w-16 shrink-0 flex-col border-r border-[--color-border] bg-[--color-bg-elevated] py-4 md:w-48">
      <div className="mb-6 hidden px-4 text-sm font-semibold tracking-tight md:block">
        Finance
      </div>
      <div className="flex flex-1 flex-col gap-1 px-2">
        <NavLink to="/upload" className={navClass} end>
          <Upload className="h-5 w-5 shrink-0" strokeWidth={1.5} />
          <span className="hidden md:inline">Upload</span>
        </NavLink>
        <NavLink to="/review" className={navClass}>
          <span className="relative">
            <ListTodo className="h-5 w-5 shrink-0" strokeWidth={1.5} />
            {reviewCount > 0 ? (
              <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-[--color-accent] px-1 text-[9px] font-medium text-white">
                {reviewCount > 99 ? "99+" : reviewCount}
              </span>
            ) : null}
          </span>
          <span className="hidden md:inline">Review</span>
        </NavLink>
        <NavLink to="/dashboard" className={navClass}>
          <LayoutDashboard className="h-5 w-5 shrink-0" strokeWidth={1.5} />
          <span className="hidden md:inline">Dashboard</span>
        </NavLink>
        <NavLink to="/analytics" className={navClass}>
          <LineChart className="h-5 w-5 shrink-0" strokeWidth={1.5} />
          <span className="hidden md:inline">Analytics</span>
        </NavLink>
        <NavLink to="/settings" className={navClass}>
          <Settings className="h-5 w-5 shrink-0" strokeWidth={1.5} />
          <span className="hidden md:inline">Settings</span>
        </NavLink>
      </div>
      <button
        type="button"
        onClick={() => void logout()}
        className="mx-2 mt-4 flex flex-col items-center gap-1 rounded-[--radius-md] px-2 py-2 text-[10px] text-[--color-text-muted] hover:bg-[--color-bg-muted] md:flex-row md:gap-2 md:px-3 md:text-xs"
      >
        <LogOut className="h-5 w-5" strokeWidth={1.5} />
        <span className="hidden md:inline">Log out</span>
      </button>
    </nav>
  );
}
