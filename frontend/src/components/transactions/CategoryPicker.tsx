import { useMemo, useState } from "react";

import type { CategoryOut } from "@/types/api";
import { cn } from "@/lib/cn";
import { Input } from "@/components/ui/input";

const RECENT_KEY = "ft-recent-categories";

function loadRecent(): number[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? parsed.filter((x) => typeof x === "number") : [];
  } catch {
    return [];
  }
}

export function saveRecentCategory(id: number) {
  const recent = loadRecent().filter((x) => x !== id);
  recent.unshift(id);
  localStorage.setItem(RECENT_KEY, JSON.stringify(recent.slice(0, 8)));
}

type Props = {
  categories: CategoryOut[];
  value: number | null;
  onChange: (categoryId: number) => void;
  disabled?: boolean;
  compact?: boolean;
};

export function CategoryPicker({
  categories,
  value,
  onChange,
  disabled,
  compact,
}: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  const recentIds = useMemo(() => loadRecent(), []);

  const sorted = useMemo(() => {
    const recentSet = new Set(recentIds);
    const recent = recentIds
      .map((id) => categories.find((c) => c.id === id))
      .filter((c): c is CategoryOut => Boolean(c));
    const rest = categories
      .filter((c) => !recentSet.has(c.id))
      .sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name));
    return [...recent, ...rest];
  }, [categories, recentIds]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return sorted;
    return sorted.filter((c) => c.name.toLowerCase().includes(q));
  }, [sorted, query]);

  const selected = categories.find((c) => c.id === value);

  return (
    <div className="relative min-w-[10rem]">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        className={cn(
          "flex w-full items-center justify-between gap-2 rounded-[--radius-md] border border-[--color-border-strong] bg-[--color-bg-elevated] px-2 py-1.5 text-left text-sm transition-colors duration-150",
          "hover:bg-[--color-bg-muted] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[--color-accent]",
          compact && "py-1 text-xs",
          disabled && "opacity-50",
        )}
      >
        <span className="flex items-center gap-1.5 truncate">
          {selected ? (
            <>
              <span aria-hidden>{selected.icon}</span>
              <span>{selected.name}</span>
            </>
          ) : (
            <span className="text-[--color-text-subtle]">Select…</span>
          )}
        </span>
        <span className="text-[--color-text-subtle]">▼</span>
      </button>
      {open ? (
        <div className="absolute right-0 z-20 mt-1 w-56 rounded-[--radius-md] border border-[--color-border] bg-[--color-bg-elevated] p-2 shadow-sm">
          <Input
            placeholder="Search categories"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="mb-2"
            autoFocus
          />
          <ul className="max-h-48 overflow-y-auto">
            {filtered.map((cat, index) => (
              <li key={cat.id}>
                <button
                  type="button"
                  className={cn(
                    "flex w-full items-center gap-2 rounded-[--radius-sm] px-2 py-1.5 text-left text-sm hover:bg-[--color-bg-muted]",
                    value === cat.id && "bg-[--color-accent-soft]",
                  )}
                  onClick={() => {
                    onChange(cat.id);
                    saveRecentCategory(cat.id);
                    setOpen(false);
                    setQuery("");
                  }}
                >
                  <span className="w-4 text-xs text-[--color-text-subtle]">
                    {index < 9 ? index + 1 : ""}
                  </span>
                  <span>{cat.icon}</span>
                  <span>{cat.name}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
