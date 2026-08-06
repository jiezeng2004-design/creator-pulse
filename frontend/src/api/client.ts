import type {
  Account,
  Comment,
  DashboardSummary,
  MetricSnapshot,
  Page,
  PlatformCapability,
  Post,
  Settings,
  SyncRun,
} from "@/types";

async function rawRequest(path: string, init?: RequestInit): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
      ...init,
    });
  } catch {
    throw new Error(
      "无法连接后端（127.0.0.1:8001）。请先运行 scripts/dev.ps1 或启动 uvicorn。",
    );
  }
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = body?.detail?.message || body?.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    if (
      res.status >= 500 &&
      (message === "Internal Server Error" || message === "Error")
    ) {
      throw new Error(
        "后端暂时不可用或返回错误。请确认后端已在 127.0.0.1:8001 运行，然后重试。",
      );
    }
    throw new Error(typeof message === "string" ? message : "请求失败");
  }
  return res;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  return rawRequest(path, init).then((res) => res.json() as Promise<T>);
}

async function requestBlob(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  return rawRequest(path, init);
}

export type QuickRefreshResult = {
  account_id: number;
  authenticated: boolean;
  needs_login: boolean;
  sync_run_id: number | null;
  sync_status: string | null;
  message: string;
  next_action: string | null;
};

export type SyncAllResult = {
  total: number;
  started: number;
  skipped: number;
  items: Array<{
    account_id: number;
    platform: string;
    status: string;
    message: string;
    sync_run_id: number | null;
  }>;
};

export type SyncCancelResult = {
  account_id: number;
  cancelling: boolean;
  message: string;
};

export type CleanupResult = {
  retention_days: number;
  cutoff: string;
  posts_deleted: number;
  comments_deleted: number;
  snapshots_deleted: number;
  sync_runs_deleted: number;
  total_deleted: number;
};

export const api = {
  health: () => request<{ status: string }>("/api/health"),
  platforms: () => request<PlatformCapability[]>("/api/platforms"),
  dashboard: () => request<DashboardSummary>("/api/dashboard/summary"),
  accounts: () => request<Account[]>("/api/accounts"),
  createAccount: (body: {
    platform: string;
    display_name?: string;
    username?: string;
    use_mock?: boolean;
    use_browser?: boolean;
  }) =>
    request<Account>("/api/accounts", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateAccount: (
    id: number,
    body: { username?: string; auth_mode?: "browser" | "api" },
  ) =>
    request<Account>(`/api/accounts/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteAccount: (id: number, deleteProfile = false) =>
    request<{ message: string }>(
      `/api/accounts/${id}?delete_profile=${deleteProfile ? "true" : "false"}`,
      { method: "DELETE" },
    ),
  login: (id: number) =>
    request<{ message: string; instructions?: string }>(
      `/api/accounts/${id}/login`,
      {
        method: "POST",
      },
    ),
  checkAuth: (id: number) =>
    request<{ authenticated: boolean; message: string; status: string }>(
      `/api/accounts/${id}/check-auth`,
      { method: "POST" },
    ),
  /** One-click: check login then enqueue a background sync when possible. */
  refreshAccount: (id: number) =>
    request<QuickRefreshResult>(`/api/accounts/${id}/refresh`, {
      method: "POST",
    }),
  syncAccount: (id: number) =>
    request<{ sync_run_id: number; status: string; message: string }>(
      `/api/accounts/${id}/sync`,
      { method: "POST" },
    ),
  syncAll: () =>
    request<SyncAllResult>("/api/accounts/sync-all", { method: "POST" }),
  /** Cancel a queued sync or ask a running sync to stop at its next checkpoint. */
  cancelSync: (id: number) =>
    request<SyncCancelResult>(`/api/accounts/${id}/cancel`, { method: "POST" }),
  posts: (params: Record<string, string | number | undefined>) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") q.set(k, String(v));
    });
    return request<Page<Post>>(`/api/posts?${q}`);
  },
  postMetrics: (id: number) =>
    request<MetricSnapshot[]>(`/api/posts/${id}/metrics`),
  comments: (params: Record<string, string | number | undefined>) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") q.set(k, String(v));
    });
    return request<Page<Comment>>(`/api/comments?${q}`);
  },
  updateCommentStatus: (id: number, local_status: string) =>
    request<Comment>(`/api/comments/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ local_status }),
    }),
  /** Bulk-set a local status on many comments in one request. */
  batchUpdateCommentStatus: (comment_ids: number[], local_status: string) =>
    request<{ updated: number; status: string }>("/api/comments/batch-status", {
      method: "POST",
      body: JSON.stringify({ comment_ids, local_status }),
    }),
  syncRuns: (params: Record<string, string | number | undefined> = {}) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") q.set(k, String(v));
    });
    return request<Page<SyncRun>>(`/api/sync-runs?${q}`);
  },
  settings: () => request<Settings>("/api/settings"),
  updateSettings: (body: Partial<Settings>) =>
    request<Settings>("/api/settings", {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  exportDatabase: () => requestBlob("/api/settings/export", { method: "POST" }),
  /** Whether an X Bearer Token is configured (the token itself is never exposed). */
  xCredentials: () =>
    request<{ configured: boolean }>("/api/settings/x-credentials"),
  /** Persist an X Bearer Token; takes effect on the next adapter use. */
  saveXCredentials: (x_bearer_token: string) =>
    request<{ configured: boolean }>("/api/settings/x-credentials", {
      method: "PUT",
      body: JSON.stringify({ x_bearer_token }),
    }),
  /** Apply the retention window now instead of waiting for the daily job. */
  cleanupNow: () =>
    request<CleanupResult>("/api/settings/cleanup", { method: "POST" }),
};
