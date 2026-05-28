import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { FormEvent, useState } from "react";
import { toast } from "sonner";

import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { ApiError, api, apiMessage } from "@/lib/api";
import type { MappingOut } from "@/types/api";

export function MappingsSection() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [source, setSource] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [search, setSearch] = useState("");
  const [editTarget, setEditTarget] = useState<MappingOut | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [pattern, setPattern] = useState("");
  const [formCategoryId, setFormCategoryId] = useState<number | "">("");

  const categories = useQuery({
    queryKey: ["categories"],
    queryFn: () => api.categories.list(),
  });

  const mappings = useQuery({
    queryKey: ["mappings", page, source, categoryId, search],
    queryFn: () =>
      api.mappings.list({
        page,
        page_size: 50,
        source: source || undefined,
        category_id: categoryId ? Number(categoryId) : undefined,
        search: search || undefined,
      }),
  });

  const save = useMutation({
    mutationFn: async () => {
      if (formCategoryId === "") throw new Error("category required");
      if (editTarget) {
        return api.mappings.patch(editTarget.id, {
          merchant_pattern: pattern,
          category_id: formCategoryId,
        });
      }
      return api.mappings.create({
        merchant_pattern: pattern,
        category_id: formCategoryId,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["mappings"] });
      void queryClient.invalidateQueries({ queryKey: ["categories"] });
      setEditTarget(null);
      setCreateOpen(false);
      setPattern("");
      setFormCategoryId("");
      toast.success("Mapping saved.");
    },
    onError: (err) => {
      toast.error(err instanceof ApiError ? apiMessage(err) : "Could not save mapping.");
    },
  });

  const remove = useMutation({
    mutationFn: (id: number) => api.mappings.delete(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["mappings"] });
      void queryClient.invalidateQueries({ queryKey: ["categories"] });
      toast.success("Mapping deleted.");
    },
    onError: (err) => {
      toast.error(err instanceof ApiError ? apiMessage(err) : "Could not delete mapping.");
    },
  });

  function openCreate() {
    setPattern("");
    setFormCategoryId(categories.data?.[0]?.id ?? "");
    setCreateOpen(true);
  }

  function openEdit(m: MappingOut) {
    setEditTarget(m);
    setPattern(m.merchant_pattern);
    setFormCategoryId(m.category_id);
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    save.mutate();
  }

  const total = mappings.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / 50));
  const categoryName = (id: number) =>
    categories.data?.find((c) => c.id === id)?.name ?? String(id);

  return (
    <section className="mt-12">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-medium text-[--color-text-muted]">
          Merchant mappings
        </h2>
        <Button variant="secondary" onClick={openCreate}>
          + Add mapping
        </Button>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        <Select
          value={source}
          onChange={(e) => {
            setSource(e.target.value);
            setPage(1);
          }}
          aria-label="Filter by source"
          className="w-auto min-w-[7rem]"
        >
          <option value="">All sources</option>
          <option value="seed">seed</option>
          <option value="llm">llm</option>
          <option value="manual">manual</option>
        </Select>
        <Select
          value={categoryId}
          onChange={(e) => {
            setCategoryId(e.target.value);
            setPage(1);
          }}
          aria-label="Filter by category"
          className="w-auto min-w-[9rem]"
        >
          <option value="">All categories</option>
          {categories.data?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
        <Input
          placeholder="Search pattern…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          className="max-w-xs flex-1"
        />
      </div>

      {mappings.isLoading ? (
        <p className="text-sm text-[--color-text-muted]">Loading…</p>
      ) : mappings.isError ? (
        <p className="text-sm text-[--color-danger]">Could not load mappings.</p>
      ) : mappings.data?.items.length === 0 ? (
        <p className="text-sm text-[--color-text-muted]">
          {search || source || categoryId
            ? "No mappings match your filter."
            : "No merchant mappings yet."}
        </p>
      ) : (
        <>
          <ul className="divide-y divide-[--color-border] border-y border-[--color-border]">
            {mappings.data?.items.map((m) => (
              <li
                key={m.id}
                className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm"
              >
                <div className="min-w-0 font-mono text-xs">{m.merchant_pattern}</div>
                <div className="flex items-center gap-3 text-[--color-text-muted]">
                  <span>{categoryName(m.category_id)}</span>
                  <span className="text-[--color-text-subtle]">{m.source}</span>
                  <Button variant="ghost" onClick={() => openEdit(m)}>
                    Edit
                  </Button>
                  <Button
                    variant="ghost"
                    disabled={remove.isPending}
                    onClick={() => remove.mutate(m.id)}
                  >
                    Delete
                  </Button>
                </div>
              </li>
            ))}
          </ul>
          {totalPages > 1 ? (
            <div className="mt-4 flex items-center justify-between text-sm">
              <Button
                variant="secondary"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <span className="text-[--color-text-muted]">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="secondary"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          ) : null}
        </>
      )}

      <Dialog
        open={createOpen || editTarget !== null}
        onClose={() => {
          setCreateOpen(false);
          setEditTarget(null);
        }}
        title={editTarget ? "Edit mapping" : "Add mapping"}
      >
        <form onSubmit={onSubmit} className="space-y-4">
          <label className="block text-sm text-[--color-text-muted]">
            Merchant pattern
            <Input
              className="mt-1 font-mono"
              value={pattern}
              onChange={(e) => setPattern(e.target.value)}
              required
            />
          </label>
          <label className="block text-sm text-[--color-text-muted]">
            Category
            <Select
              className="mt-1"
              value={formCategoryId}
              onChange={(e) => setFormCategoryId(Number(e.target.value))}
              required
            >
              {categories.data?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </label>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setCreateOpen(false);
                setEditTarget(null);
              }}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={save.isPending}>
              {save.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
              ) : null}
              Save
            </Button>
          </div>
        </form>
      </Dialog>
    </section>
  );
}
