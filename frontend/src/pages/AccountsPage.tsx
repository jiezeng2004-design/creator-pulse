import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  LogIn,
  Plus,
  RefreshCw,
  SearchCheck,
  Trash2,
  Users,
  XCircle,
} from "lucide-react";
import { api } from "@/api/client";
import { useInvalidateAll } from "@/hooks/useInvalidateAll";
import { useSyncEvents } from "@/hooks/useSyncEvents";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Notice } from "@/components/ui/Notice";
import { CardListSkeleton } from "@/components/ui/Skeleton";
import { PageHeader } from "@/components/layout/PageHeader";
import { PlatformIcon } from "@/components/platform/PlatformIcon";
import {
  PLATFORM_LABEL,
  PHASE_LABEL,
  STATUS_LABEL,
  relativeTime,
  statusTone,
} from "@/lib/format";
import { QUICK_PLATFORMS, PLATFORMS } from "@/lib/platforms";

export function AccountsPage() {
  const invalidateAll = useInvalidateAll();
  const [platform, setPlatform] = useState("zhihu");
  const [name, setName] = useState("");
  const [xUsername, setXUsername] = useState("");
  const [xMode, setXMode] = useState<"browser" | "api">("browser");
  const [useMock, setUseMock] = useState(false);
  const [message, setMessage] = useState("");
  const [usernameDraft, setUsernameDraft] = useState<{ id: number; value: string } | null>(null);
  const [pendingAction, setPendingAction] = useState<{
    id: number;
    type: string;
  } | null>(null);

  const { data: accounts = [], isLoading } = useQuery({
    queryKey: ["accounts"],
    queryFn: api.accounts,
    staleTime: 2_000,
    refetchInterval: 30_000,
  });
  const platforms = useQuery({ queryKey: ["platforms"], queryFn: api.platforms });
  // Live progress hints come from the SSE stream; the query refetches on events.
  const { progress } = useSyncEvents();

  const createMut = useMutation({
    mutationFn: (opts?: { platform?: string; use_mock?: boolean; autoLogin?: boolean }) =>
      api.createAccount({
        platform: opts?.platform || platform,
        display_name: name || undefined,
        username:
          (opts?.platform || platform) === "x"
            ? (opts?.use_mock ? undefined : xUsername.trim() || undefined)
            : undefined,
        use_mock: opts?.use_mock ?? useMock,
        use_browser:
          (opts?.platform || platform) === "x" && !opts?.use_mock
            ? xMode === "browser"
            : undefined,
      }),
    onSuccess: async (acc, vars) => {
      invalidateAll();
      setName("");
      if (vars?.autoLogin && !acc.is_mock) {
        try {
          const login = await api.login(acc.id);
          setMessage(`已添加并打开登录：${login.message}`);
        } catch (e) {
          setMessage(`账号已添加，但打开登录失败：${(e as Error).message}`);
        }
        invalidateAll();
        return;
      }
      if (acc.platform === "x") {
        setXUsername("");
      }
      if (acc.is_mock) {
        try {
          const r = await api.refreshAccount(acc.id);
          setMessage(`演示账号已添加：${r.message}`);
        } catch {
          setMessage("演示账号已添加，可点击「一键同步」");
        }
        invalidateAll();
        return;
      }
      setMessage(
        acc.platform === "x" && acc.authentication_type === "api_token"
          ? "X 账号已添加。请到「设置 → X API 配置」填入 Bearer Token，然后点「检查并同步」。"
          : "账号已添加。点击主按钮打开登录，完成后点「检查并同步」。",
      );
    },
    onError: (e: Error) => setMessage(e.message),
  });

  const saveUsername = useMutation({
    mutationFn: ({ id, value }: { id: number; value: string }) =>
      api.updateAccount(id, { username: value }),
    onSuccess: (acc) => {
      invalidateAll();
      setUsernameDraft(null);
      setMessage(acc.platform === "x" ? `已保存 X 用户名 @${acc.username}。可点击「检查并同步」。` : "已保存用户名");
    },
    onError: (e: Error) => setMessage(e.message),
  });

  const switchXMode = useMutation({
    mutationFn: ({ id, mode }: { id: number; mode: "browser" | "api" }) =>
      api.updateAccount(id, { auth_mode: mode }),
    onSuccess: (_acc, vars) => {
      invalidateAll();
      setMessage(
        vars.mode === "browser"
          ? "已切换到浏览器登录模式（免费，不消耗 API 额度）。请点「打开登录」在浏览器中登录 x.com。"
          : "已切换到 API Token 模式。请到设置页配置 Bearer Token，需要有效额度。",
      );
    },
    onError: (e: Error) => setMessage(e.message),
  });

  const action = useMutation({
    mutationFn: async ({
      id,
      type,
      deleteProfile,
    }: {
      id: number;
      type: "login" | "check" | "sync" | "refresh" | "cancel" | "delete";
      deleteProfile?: boolean;
    }) => {
      setPendingAction({ id, type });
      if (type === "login") return api.login(id);
      if (type === "check") return api.checkAuth(id);
      if (type === "sync") return api.syncAccount(id);
      if (type === "refresh") return api.refreshAccount(id);
      if (type === "cancel") return api.cancelSync(id);
      return api.deleteAccount(id, deleteProfile);
    },
    onSuccess: (res) => {
      invalidateAll();
      const msg =
        (res as { message?: string; instructions?: string }).message ||
        (res as { instructions?: string }).instructions ||
        "完成";
      setMessage(msg);
    },
    onError: (e: Error) => setMessage(e.message),
    onSettled: () => setPendingAction(null),
  });

  const actionLoading = (id: number, type: string) =>
    pendingAction?.id === id && pendingAction.type === type;

  const primaryFor = (a: (typeof accounts)[0]) => {
    const na = a.next_action;
    if (!na) return { type: "refresh" as const, label: "一键同步" };
    if (na.action === "login") return { type: "login" as const, label: na.label };
    if (na.action === "check_auth") return { type: "check" as const, label: na.label };
    if (na.action === "sync") return { type: "sync" as const, label: na.label };
    if (na.action === "wait") return { type: "refresh" as const, label: na.label };
    return { type: "refresh" as const, label: na.label || "检查并同步" };
  };

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="04 / 账号矩阵"
        title="账号管理"
        description="推荐路径：点平台快捷添加 → 登录 →「检查并同步」。删除浏览器 Profile 仍需二次确认。"
      />

      {message && (
        <Notice tone="info" onDismiss={() => setMessage("")}>
          {message}
        </Notice>
      )}

      <Card>
        <div className="mb-3 font-mono text-[11px] font-medium uppercase tracking-[0.18em] text-ink-500 dark:text-[#9aa19b]">
          快捷添加
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {QUICK_PLATFORMS.map((p) => (
            <Button
              key={p.id}
              size="sm"
              variant="secondary"
              disabled={createMut.isPending}
              onClick={() => {
                if (p.id === "x" && xMode === "api" && !xUsername.trim()) {
                  setPlatform("x");
                  setMessage("请先在下方「自定义添加」中填写 X 用户名（不含 @）");
                  return;
                }
                createMut.mutate({
                  platform: p.id,
                  use_mock: false,
                  autoLogin: p.id !== "x" || xMode === "browser",
                });
              }}
            >
              <PlatformIcon platform={p.id} size="sm" className="!h-6 !w-6 !rounded-md !text-[9px]" />
              {p.label}
              {p.id !== "x" || xMode === "browser" ? " 并登录" : ""}
            </Button>
          ))}
          <Button
            size="sm"
            variant="ghost"
            disabled={createMut.isPending}
            onClick={() => createMut.mutate({ platform: "zhihu", use_mock: true })}
          >
            <Plus className="h-3.5 w-3.5" aria-hidden />
            演示数据
          </Button>
        </div>
        <div className="mt-5 border-t border-ink-900/8 pt-4 dark:border-white/10">
          <div className="mb-3 font-mono text-[11px] font-medium uppercase tracking-[0.18em] text-ink-500 dark:text-[#9aa19b]">
            自定义添加
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <label className="block text-sm">
              <span className="mb-1 block text-ink-500 dark:text-[#9aa19b]">平台</span>
              <select
                className="block w-full rounded-md border border-ink-900/15 bg-transparent px-2 py-1.5 dark:border-white/15"
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
              >
                {PLATFORMS.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="mb-1 block text-ink-500 dark:text-[#9aa19b]">显示名称</span>
              <input
                className="block w-full rounded-md border border-ink-900/15 bg-transparent px-2 py-1.5 dark:border-white/15"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="可选"
              />
            </label>
            {platform === "x" && (
              <label className="block text-sm">
                <span className="mb-1 block text-ink-500 dark:text-[#9aa19b]">X 获取方式</span>
                <select
                  className="block w-full rounded-md border border-ink-900/15 bg-transparent px-2 py-1.5 dark:border-white/15"
                  value={xMode}
                  onChange={(e) => setXMode(e.target.value as "browser" | "api")}
                >
                  <option value="browser">浏览器登录（免费，不消耗额度）</option>
                  <option value="api">官方 API Token（消耗额度）</option>
                </select>
              </label>
            )}
            {platform === "x" && xMode === "api" && (
              <label className="block text-sm">
                <span className="mb-1 block text-ink-500 dark:text-[#9aa19b]">X 用户名</span>
                <input
                  className="block w-full rounded-md border border-ink-900/15 bg-transparent px-2 py-1.5 dark:border-white/15"
                  value={xUsername}
                  onChange={(e) => setXUsername(e.target.value)}
                  placeholder="不含 @，例如 elonmusk"
                />
                <span className="mt-1 block text-xs text-ink-400">
                  必填：用于 app-only Bearer Token 查询你的账号
                </span>
              </label>
            )}
            <div className="flex items-end gap-2 sm:col-span-2 lg:col-span-1">
              <label className="flex h-9 items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={useMock}
                  onChange={(e) => setUseMock(e.target.checked)}
                />
                演示数据
              </label>
              <Button
                className="h-9"
                onClick={() =>
                  createMut.mutate({
                    platform,
                    use_mock: useMock,
                    autoLogin: !useMock && (platform !== "x" || xMode === "browser"),
                  })
                }
                disabled={createMut.isPending}
              >
                添加
              </Button>
            </div>
          </div>
          {platforms.data?.find((p) => p.platform === platform)?.experimental && (
            <div className="mt-2">
              <Badge tone="warn">该平台适配器为实验性</Badge>
            </div>
          )}
        </div>
      </Card>

      {isLoading && <CardListSkeleton rows={3} />}

      {!isLoading && accounts.length === 0 && (
        <EmptyState
          title="尚未绑定账号"
          description="点击上方「+ 知乎 并登录」可最少步骤开始；或添加演示数据快速预览界面。"
          icon={Users}
          actions={[
            {
              label: "添加知乎并登录",
              primary: true,
              onClick: () =>
                createMut.mutate({ platform: "zhihu", use_mock: false, autoLogin: true }),
            },
            {
              label: "添加演示数据",
              onClick: () => createMut.mutate({ platform: "zhihu", use_mock: true }),
            },
          ]}
        />
      )}

      <div className="grid gap-3">
        {!isLoading && accounts.map((a) => {
          const primary = primaryFor(a);
          const prog = progress[a.id];
          const statusColor =
            a.account_status === "connected"
              ? "#0a7357"
              : a.account_status === "error"
                ? "#be123c"
                : a.account_status === "syncing"
                  ? "#2f4fd0"
                  : "#b45309";
          return (
            <Card
              key={a.id}
              hoverable
              className="animate-fade-in overflow-hidden p-0"
            >
              <div className="h-1 w-full" style={{ backgroundColor: statusColor }} aria-hidden />
              <div className="flex flex-wrap items-start justify-between gap-3 px-5 py-5">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-3">
                    <PlatformIcon platform={a.platform} size="lg" />
                    <span className="text-lg font-semibold tracking-tight">{a.display_name}</span>
                    <Badge tone={statusTone(a.account_status)} dot>
                      {STATUS_LABEL[a.account_status] || a.account_status}
                    </Badge>
                    {a.is_mock && <Badge tone="mock">演示数据</Badge>}
                  </div>
                  <div className="mt-2 space-y-0.5 text-xs text-ink-500 dark:text-[#9aa19b]">
                    <div>
                      {PLATFORM_LABEL[a.platform] || a.platform} ·{" "}
                      {a.username ? `@${a.username}` : "用户名：—"} · 认证{" "}
                      {a.authentication_type}
                    </div>
                    {a.platform === "x" && a.authentication_type === "api_token" && !a.username && (
                      <div className="flex flex-wrap items-center gap-2 pt-1">
                        {usernameDraft?.id === a.id ? (
                          <>
                            <input
                              className="w-44 rounded-md border border-ink-900/15 bg-transparent px-2 py-1 text-xs dark:border-white/15"
                              value={usernameDraft.value}
                              onChange={(e) => setUsernameDraft({ id: a.id, value: e.target.value })}
                              placeholder="X 用户名（不含 @），如 elonmusk"
                              onKeyDown={(e) => {
                                if (e.key === "Enter" && usernameDraft.value.trim()) {
                                  saveUsername.mutate({ id: a.id, value: usernameDraft.value });
                                }
                              }}
                            />
                            <button
                              className="text-brand-600 hover:underline"
                              disabled={saveUsername.isPending || !usernameDraft.value.trim()}
                              onClick={() =>
                                saveUsername.mutate({ id: a.id, value: usernameDraft.value })
                              }
                            >
                              {saveUsername.isPending ? "保存中…" : "保存"}
                            </button>
                            <button
                              className="text-ink-400 hover:underline"
                              onClick={() => setUsernameDraft(null)}
                            >
                              取消
                            </button>
                          </>
                        ) : (
                          <button
                            className="text-brand-600 hover:underline"
                            onClick={() => setUsernameDraft({ id: a.id, value: "" })}
                          >
                            X 账号需填写用户名才能用 Bearer Token 查询，点击填写
                          </button>
                        )}
                      </div>
                    )}
                    {a.platform === "x" && (
                      <div className="flex flex-wrap items-center gap-2 pt-1">
                        {a.authentication_type === "browser_profile" ? (
                          <>
                            <span className="text-ink-400">当前：浏览器登录模式（免 API 额度）</span>
                            <button
                              className="text-brand-600 hover:underline"
                              disabled={switchXMode.isPending}
                              onClick={() => switchXMode.mutate({ id: a.id, mode: "api" })}
                            >
                              切换到 API Token 模式
                            </button>
                          </>
                        ) : (
                          <>
                            <span className="text-ink-400">当前：API Token 模式（消耗额度）</span>
                            <button
                              className="text-brand-600 hover:underline"
                              disabled={switchXMode.isPending}
                              onClick={() => switchXMode.mutate({ id: a.id, mode: "browser" })}
                            >
                              切换到浏览器登录模式（免费）
                            </button>
                          </>
                        )}
                      </div>
                    )}
                    <div>最后成功同步：{relativeTime(a.last_successful_sync_at)}</div>
                    {prog && (
                      <div className="flex flex-wrap items-center gap-2 text-brand-600 dark:text-brand-300">
                        <span className="inline-flex h-3 w-3 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
                        {phaseLabel(prog)}
                        {prog.posts_fetched != null && prog.posts_fetched > 0 && (
                          <span className="tabular-nums">
                            内容 {prog.posts_fetched} · 评论 {prog.comments_fetched ?? 0}
                          </span>
                        )}
                        {prog.message && <span className="text-ink-500">{prog.message}</span>}
                      </div>
                    )}
                    {prog && (prog.posts_fetched ?? 0) > 0 && (
                      <div className="h-1 w-full max-w-xs overflow-hidden rounded-full bg-ink-900/5 dark:bg-white/10">
                        <div className="h-full w-1/3 animate-pulse rounded-full bg-brand-500" />
                      </div>
                    )}
                    {a.next_action && (
                      <div className="text-ink-600 dark:text-[#c6cac2]">
                        建议：{a.next_action.description}
                      </div>
                    )}
                    {a.last_sync_error && (
                      <div className="text-rose-600">错误：{a.last_sync_error}</div>
                    )}
                    {a.browser_profile_path && (
                      <div className="truncate">Profile：…/{a.browser_profile_path}</div>
                    )}
                  </div>
                  <div className="mt-2 flex gap-3 text-xs">
                    <Link
                      className="text-brand-600 hover:underline"
                      to={`/posts?platform=${a.platform}`}
                    >
                      查看内容
                    </Link>
                    <Link
                      className="text-brand-600 hover:underline"
                      to={`/comments?platform=${a.platform}`}
                    >
                      查看评论
                    </Link>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    loading={actionLoading(a.id, primary.type)}
                    disabled={action.isPending || a.account_status === "syncing"}
                    onClick={() => action.mutate({ id: a.id, type: primary.type })}
                  >
                    {primary.type === "login" && (
                      <LogIn className="h-3.5 w-3.5" aria-hidden />
                    )}
                    {(primary.type === "sync" || primary.type === "refresh") && (
                      <RefreshCw className="h-3.5 w-3.5" aria-hidden />
                    )}
                    {primary.type === "check" && (
                      <SearchCheck className="h-3.5 w-3.5" aria-hidden />
                    )}
                    {primary.label}
                  </Button>
                  {a.account_status === "syncing" && (
                    <Button
                      size="sm"
                      variant="secondary"
                      loading={actionLoading(a.id, "cancel")}
                      onClick={() => action.mutate({ id: a.id, type: "cancel" })}
                    >
                      <XCircle className="h-3.5 w-3.5" aria-hidden />
                      取消同步
                    </Button>
                  )}
                  {primary.type !== "login" && a.authentication_type === "browser_profile" && !a.is_mock && (
                    <Button
                      size="sm"
                      variant="secondary"
                      loading={actionLoading(a.id, "login")}
                      onClick={() => action.mutate({ id: a.id, type: "login" })}
                    >
                      <LogIn className="h-3.5 w-3.5" aria-hidden />
                      打开登录
                    </Button>
                  )}
                  {primary.type !== "refresh" && a.account_status !== "syncing" && (
                    <Button
                      size="sm"
                      variant="secondary"
                      loading={actionLoading(a.id, "refresh")}
                      onClick={() => action.mutate({ id: a.id, type: "refresh" })}
                    >
                      <SearchCheck className="h-3.5 w-3.5" aria-hidden />
                      检查并同步
                    </Button>
                  )}
                  <div className="ml-1 flex items-center gap-1 border-l border-ink-900/10 pl-3 dark:border-white/10">
                    <Button
                      size="sm"
                      variant="ghost"
                      title="删除绑定（保留浏览器 Profile）"
                      aria-label="删除绑定（保留浏览器 Profile）"
                      loading={actionLoading(a.id, "delete")}
                      onClick={() => {
                        if (confirm("确定删除本地账号绑定？默认不删除浏览器 Profile。")) {
                          action.mutate({ id: a.id, type: "delete", deleteProfile: false });
                        }
                      }}
                    >
                      <Trash2 className="h-3.5 w-3.5" aria-hidden />
                    </Button>
                    <Button
                      size="sm"
                      variant="danger"
                      title="删除绑定并清理浏览器 Profile（不可恢复）"
                      aria-label="删除绑定并清理浏览器 Profile（不可恢复）"
                      onClick={() => {
                        if (
                          confirm(
                            "将删除本地账号绑定，并清理浏览器 Profile 目录。此操作不可恢复。确认？",
                          )
                        ) {
                          action.mutate({ id: a.id, type: "delete", deleteProfile: true });
                        }
                      }}
                    >
                      <Trash2 className="h-3.5 w-3.5" aria-hidden />
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

function phaseLabel(p: { phase: string; status: string }): string {
  if (p.status === "success") return "同步完成";
  if (p.status === "failed") return "同步失败";
  if (p.status === "cancelled") return "同步已取消";
  return PHASE_LABEL[p.phase] || "同步中";
}
