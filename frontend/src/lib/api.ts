import type {
  AnswerOut,
  BulkCategorize,
  CategoryCreate,
  CategoryOut,
  CategoryPatch,
  DashboardOut,
  InsightsOut,
  MappingCreate,
  MappingOut,
  MappingPatch,
  MeOut,
  MoMOut,
  PaginatedMappings,
  PaginatedTransactions,
  ParsedSummary,
  StatementOut,
  TransactionOut,
  TrendOut,
} from "@/types/api";

/** Dev: direct to localhost. Prod: same-origin via vercel.json rewrites (first-party cookies). */
function resolveApiBase(): string {
  if (!import.meta.env.DEV) {
    return "";
  }
  const raw = import.meta.env.VITE_API_URL;
  return (raw?.trim() || "http://localhost:8000").replace(/\/+$/, "");
}

const BASE = resolveApiBase();

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

  if (res.status === 401 && !path.startsWith("/api/auth/login")) {
    // Don't hard-redirect when already on /login — Login calls /api/auth/me on
    // mount; a reload loop there blinks the screen and blocks password input.
    if (window.location.pathname !== "/login") {
      window.location.assign("/login");
    }
    throw new ApiError(401, null);
  }

  if (res.status === 204) return undefined as T;

  const body = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, body);
  return body as T;
}

function apiMessage(err: ApiError): string {
  const body = err.body as { message?: string } | null;
  return body?.message ?? "Something went wrong. Try again.";
}

export { apiMessage };

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
    create: (body: CategoryCreate) =>
      request<CategoryOut>("/api/categories", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    patch: (id: number, body: CategoryPatch) =>
      request<CategoryOut>(`/api/categories/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    delete: (id: number, moveTo?: number) => {
      const q = moveTo != null ? `?move_to=${moveTo}` : "";
      return request<void>(`/api/categories/${id}${q}`, { method: "DELETE" });
    },
  },

  mappings: {
    list: (params: Record<string, string | number | undefined>) => {
      const q = new URLSearchParams();
      for (const [k, v] of Object.entries(params)) {
        if (v !== undefined && v !== "") q.set(k, String(v));
      }
      return request<PaginatedMappings>(`/api/mappings?${q}`);
    },
    create: (body: MappingCreate) =>
      request<MappingOut>("/api/mappings", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    patch: (id: number, body: MappingPatch) =>
      request<MappingOut>(`/api/mappings/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    delete: (id: number) =>
      request<void>(`/api/mappings/${id}`, { method: "DELETE" }),
  },

  exportTransactionsCsv: async (params?: { from?: string; to?: string }) => {
    const q = new URLSearchParams();
    if (params?.from) q.set("from", params.from);
    if (params?.to) q.set("to", params.to);
    const qs = q.toString();
    const res = await fetch(
      `${BASE}/api/transactions/export.csv${qs ? `?${qs}` : ""}`,
      { credentials: "include" },
    );
    if (res.status === 401) {
      window.location.assign("/login");
      throw new ApiError(401, null);
    }
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new ApiError(res.status, body);
    }
    return res.blob();
  },

  analytics: {
    dashboard: (month: number, year: number) =>
      request<DashboardOut>(`/api/analytics/dashboard/${month}/${year}`),
    mom: () => request<MoMOut>("/api/analytics/mom"),
    trends: (categoryId: number, from?: string, to?: string) => {
      const q = new URLSearchParams();
      if (from) q.set("from", from);
      if (to) q.set("to", to);
      const qs = q.toString();
      return request<TrendOut>(
        `/api/analytics/trends/${categoryId}${qs ? `?${qs}` : ""}`,
      );
    },
    insights: (body: { month: number; year: number }, force = false) =>
      request<InsightsOut>(
        `/api/analytics/insights${force ? "?force=true" : ""}`,
        {
          method: "POST",
          body: JSON.stringify(body),
        },
      ),
    ask: (body: { question: string; month: number; year: number }) =>
      request<AnswerOut>("/api/analytics/ask", {
        method: "POST",
        body: JSON.stringify(body),
      }),
  },
};
