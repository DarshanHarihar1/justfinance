import type {
  BulkCategorize,
  CategoryOut,
  MeOut,
  PaginatedTransactions,
  ParsedSummary,
  StatementOut,
  TransactionOut,
} from "@/types/api";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
  ) {
    super(`API ${status}`);
    this.name = "ApiError";
  }
}

export function getApiBase(): string {
  return BASE;
}

async function request<T>(
  path: string,
  init: Parameters<typeof fetch>[1] = {},
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };
  if (init.body && !(init.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${BASE}${path}`, {
    ...init,
    credentials: "include",
    headers,
  });

  if (res.status === 204) return undefined as T;

  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, body);
  return body as T;
}

export const api = {
  healthz: () => request<{ status: string }>("/healthz"),

  auth: {
    login: (password: string) =>
      request<void>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ password }),
      }),
    logout: () => request<void>("/api/auth/logout", { method: "POST" }),
    me: () => request<MeOut>("/api/auth/me"),
  },

  statements: {
    upload: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return request<ParsedSummary>("/api/statements/upload", {
        method: "POST",
        body: fd,
      });
    },
    list: () => request<StatementOut[]>("/api/statements"),
    get: (id: number) => request<StatementOut>(`/api/statements/${id}`),
    review: (id: number) => request<TransactionOut[]>(`/api/statements/${id}/review`),
    delete: (id: number) => request<void>(`/api/statements/${id}`, { method: "DELETE" }),
  },

  transactions: {
    list: (params: Record<string, string | number | boolean | undefined>) => {
      const q = new URLSearchParams();
      for (const [k, v] of Object.entries(params)) {
        if (v !== undefined && v !== null) q.set(k, String(v));
      }
      return request<PaginatedTransactions>(`/api/transactions?${q}`);
    },
    categorize: (body: BulkCategorize) =>
      request<void>("/api/transactions/categorize", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    patch: (
      id: number,
      body: { category_id?: number | null; notes?: string | null; remember?: boolean },
    ) =>
      request<TransactionOut>(`/api/transactions/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
  },

  categories: {
    list: () => request<CategoryOut[]>("/api/categories"),
  },
};
