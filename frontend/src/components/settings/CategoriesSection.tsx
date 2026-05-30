import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { FormEvent, useState } from "react";
import { toast } from "sonner";

import { Dialog } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { ApiError, api, apiMessage } from "@/lib/api";
import type { CategoryOut } from "@/types/api";

type FormState = {
  name: string;
  color: string;
  icon: string;
  sort_order: number;
};

const emptyForm = (): FormState => ({
  name: "",
  color: "#4CAF50",
  icon: "📦",
  sort_order: 100,
});

export function CategoriesSection() {
  const queryClient = useQueryClient();
  const [editTarget, setEditTarget] = useState<CategoryOut | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<CategoryOut | null>(null);
  const [moveTo, setMoveTo] = useState<number | "">("");
  const [form, setForm] = useState<FormState>(emptyForm);

  const categories = useQuery({
    queryKey: ["categories"],
    queryFn: () => api.categories.list(),
  });

  const save = useMutation({
    mutationFn: async () => {
      if (editTarget) {
        return api.categories.patch(editTarget.id, {
          name: form.name,
          color: form.color,
          icon: form.icon,
          sort_order: form.sort_order,
        });
      }
      return api.categories.create({
        name: form.name,
        color: form.color,
        icon: form.icon,
        sort_order: form.sort_order,
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["categories"] });
      setEditTarget(null);
      setCreateOpen(false);
      toast.success("Category saved.");
    },
    onError: (err) => {
      toast.error(err instanceof ApiError ? apiMessage(err) : "Could not save category.");
    },
  });

  const remove = useMutation({
    mutationFn: () => {
      if (!deleteTarget) throw new Error("no target");
      const targetId = moveTo === "" ? undefined : Number(moveTo);
      return api.categories.delete(deleteTarget.id, targetId);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["categories"] });
      setDeleteTarget(null);
      setMoveTo("");
      toast.success("Category deleted.");
    },
    onError: (err) => {
      toast.error(err instanceof ApiError ? apiMessage(err) : "Could not delete category.");
    },
  });

  function openCreate() {
    setForm(emptyForm());
    setCreateOpen(true);
  }

  function openEdit(cat: CategoryOut) {
    setEditTarget(cat);
    setForm({
      name: cat.name,
      color: cat.color,
      icon: cat.icon,
      sort_order: cat.sort_order,
    });
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    save.mutate();
  }

  const dialogOpen = createOpen || editTarget !== null;
  const needsMove = Boolean(
    deleteTarget &&
      (deleteTarget.mapping_count > 0 || deleteTarget.transaction_count > 0),
  );

  return (
    <section>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-medium text-[--color-text-muted]">Categories</h2>
        <Button variant="secondary" onClick={openCreate}>
          + New category
        </Button>
      </div>

      {categories.isLoading ? (
        <p className="text-sm text-[--color-text-muted]">Loading…</p>
      ) : categories.isError ? (
        <p className="text-sm text-[--color-danger]">Could not load categories.</p>
      ) : (
        <ul className="divide-y divide-[--color-border] border-y border-[--color-border]">
          {categories.data?.map((cat) => (
            <li
              key={cat.id}
              className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm"
            >
              <div className="flex min-w-0 items-center gap-3">
                <span className="text-lg" aria-hidden>
                  {cat.icon}
                </span>
                <span
                  className="h-3 w-3 shrink-0 rounded-full"
                  style={{ backgroundColor: cat.color }}
                />
                <span className="font-medium">{cat.name}</span>
                <span className="text-[--color-text-subtle]">
                  {cat.mapping_count} mapping{cat.mapping_count === 1 ? "" : "s"}
                </span>
                {cat.is_system ? (
                  <span className="rounded bg-[--color-bg-muted] px-1.5 py-0.5 text-xs text-[--color-text-subtle]">
                    System
                  </span>
                ) : null}
              </div>
              <div className="flex gap-2">
                <Button variant="ghost" onClick={() => openEdit(cat)}>
                  Edit
                </Button>
                <Button
                  variant="ghost"
                  disabled={cat.is_system}
                  onClick={() => {
                    setDeleteTarget(cat);
                    setMoveTo("");
                  }}
                >
                  Delete
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <Dialog
        open={dialogOpen}
        onClose={() => {
          setCreateOpen(false);
          setEditTarget(null);
        }}
        title={editTarget ? "Edit category" : "New category"}
      >
        <form onSubmit={onSubmit} className="space-y-4">
          <label className="block text-sm text-[--color-text-muted]">
            Name
            <Input
              className="mt-1"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              required
            />
          </label>
          <label className="block text-sm text-[--color-text-muted]">
            Color (hex)
            <Input
              className="mt-1 font-mono"
              value={form.color}
              onChange={(e) => setForm((f) => ({ ...f, color: e.target.value }))}
            />
          </label>
          <label className="block text-sm text-[--color-text-muted]">
            Icon (emoji)
            <Input
              className="mt-1"
              value={form.icon}
              onChange={(e) => setForm((f) => ({ ...f, icon: e.target.value }))}
            />
          </label>
          <label className="block text-sm text-[--color-text-muted]">
            Sort order
            <Input
              className="mt-1"
              type="number"
              value={form.sort_order}
              onChange={(e) =>
                setForm((f) => ({ ...f, sort_order: Number(e.target.value) }))
              }
            />
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

      <Dialog
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        title="Delete category"
      >
        {deleteTarget ? (
          <div className="space-y-4">
            <p className="text-sm text-[--color-text-muted]">
              Delete <strong>{deleteTarget.name}</strong>?
              {needsMove
                ? " Choose a category to move existing mappings and transactions to."
                : null}
            </p>
            {needsMove ? (
              <label className="block text-sm text-[--color-text-muted]">
                Move to
                <Select
                  className="mt-1"
                  value={moveTo}
                  onChange={(e) =>
                    setMoveTo(e.target.value ? Number(e.target.value) : "")
                  }
                  required
                >
                  <option value="">Select…</option>
                  {categories.data
                    ?.filter((c) => c.id !== deleteTarget.id)
                    .map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                </Select>
              </label>
            ) : null}
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setDeleteTarget(null)}>
                Cancel
              </Button>
              <Button
                variant="danger"
                disabled={remove.isPending || (needsMove && moveTo === "")}
                onClick={() => remove.mutate()}
              >
                {remove.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                ) : null}
                Delete
              </Button>
            </div>
          </div>
        ) : null}
      </Dialog>
    </section>
  );
}
