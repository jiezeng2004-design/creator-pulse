import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import clsx from "clsx";
import {
  FileText,
  LayoutDashboard,
  Menu,
  MessageSquare,
  Moon,
  RefreshCw,
  Search,
  Settings,
  Sun,
  Users,
  X,
} from "lucide-react";
import { api } from "@/api/client";
import { useInvalidateAll } from "@/hooks/useInvalidateAll";
import { useNotifyOnSyncEvent } from "@/hooks/useSyncNotification";
import { useSyncEvents } from "@/hooks/useSyncEvents";
import { Button } from "@/components/ui/Button";
import { useTheme } from "@/lib/theme";
import { ErrorBoundary } from "@/components/layout/ErrorBoundary";
import { CommandPalette } from "@/components/layout/CommandPalette";

const nav = [
  { to: "/", label: "总览", icon: LayoutDashboard },
  { to: "/posts", label: "内容", icon: FileText },
  { to: "/comments", label: "评论", icon: MessageSquare },
  { to: "/accounts", label: "账号", icon: Users },
  { to: "/sync-runs", label: "同步", icon: RefreshCw },
  { to: "/settings", label: "设置", icon: Settings },
];

export function AppShell() {
  const { theme, toggle } = useTheme();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const location = useLocation();
  const invalidateAll = useInvalidateAll();
  // Live sync progress replaces 2s polling: the SSE stream invalidates the
  // affected queries the moment a stage changes. A slow 30s interval remains
  // as a fallback so a dropped connection cannot freeze the UI silently.
  const { connected, lastTerminal } = useSyncEvents();
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings, staleTime: 60_000 });
  const accounts = useQuery({
    queryKey: ["accounts"],
    queryFn: api.accounts,
    staleTime: 2_000,
    refetchInterval: 30_000,
  });
  const accountLabel =
    (lastTerminal &&
      accounts.data?.find((a) => a.id === lastTerminal.account_id)?.display_name) ||
    null;
  useNotifyOnSyncEvent(
    lastTerminal?.status ?? null,
    accountLabel,
    lastTerminal?.run_id ?? null,
  );
  // Backend health probe: surfaces a banner the moment the local API is
  // unreachable, and clears it automatically when it recovers.
  const health = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    refetchInterval: 10_000,
    retry: 0,
    staleTime: 0,
  });
  const backendDown = health.isError;
  const hasActiveSync = accounts.data?.some((account) => account.account_status === "syncing");
  const dash = useQuery({
    queryKey: ["dashboard"],
    queryFn: api.dashboard,
    staleTime: hasActiveSync ? 0 : 60_000,
  });

  const mockMode = settings.data?.enable_mock_data || dash.data?.mock_mode;
  const pending = dash.data?.pending_comments ?? 0;
  const hasAccounts = (accounts.data?.length ?? 0) > 0;
  const syncingAccounts = accounts.data?.filter(
    (account) => account.account_status === "syncing",
  );
  const syncingCount = syncingAccounts?.length ?? 0;

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandOpen((open) => !open);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [location.pathname]);

  const syncAll = useMutation({
    mutationFn: api.syncAll,
    onSuccess: () => invalidateAll(),
  });

  const navLinks = (
    <nav className="flex items-center gap-1">
      {nav.map((item) => {
        const Icon = item.icon;
        return (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            onClick={() => setMobileNavOpen(false)}
            className={({ isActive }) =>
              clsx(
                "relative flex items-center gap-1.5 px-2.5 py-1.5 text-sm transition-colors",
                isActive
                  ? "font-medium text-ink-900 after:absolute after:inset-x-2 after:-bottom-px after:h-0.5 after:rounded-full after:bg-ink-900 dark:text-[#e6e8e3] dark:after:bg-[#e6e8e3]"
                  : "text-ink-500 hover:text-ink-900 dark:text-[#9aa19b] dark:hover:text-[#e6e8e3]",
              )
            }
          >
            <Icon className="h-4 w-4" aria-hidden />
            <span className="hidden lg:inline">{item.label}</span>
            {item.to === "/comments" && pending > 0 && (
              <span className="rounded-full bg-brand-600 px-1.5 py-0.5 text-[10px] font-semibold text-white">
                {pending}
              </span>
            )}
          </NavLink>
        );
      })}
    </nav>
  );

  return (
    <div className="min-h-screen bg-cream-100 text-ink-900 dark:bg-[#121512] dark:text-[#e6e8e3]">
      <div className="min-w-0">
        {mockMode && (
          <div className="bg-brand-700 px-4 py-1.5 text-center text-xs font-medium tracking-wide text-white">
            演示数据模式 — 当前为 Mock 示例，非真实平台数据
          </div>
        )}
        {backendDown && (
          <div className="bg-rose-700 px-4 py-1.5 text-center text-xs font-medium tracking-wide text-white">
            无法连接本地后端（127.0.0.1:8001）— 正在自动重试… 请确认后端已启动
          </div>
        )}
        <header className="sticky top-0 z-30 border-b border-ink-900/8 bg-cream-100/85 backdrop-blur-md dark:border-white/10 dark:bg-[#121512]/85">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-3 md:px-8">
            <NavLink to="/" end className="flex items-center gap-2.5">
              <span className="flex h-7 w-7 items-center justify-center rounded-md bg-ink-900 font-mono text-[11px] font-semibold text-cream-100 dark:bg-[#e6e8e3] dark:text-[#121512]">
                CP
              </span>
              <span className="text-[15px] font-semibold tracking-tight">
                CreatorPulse
              </span>
            </NavLink>
            <div className="hidden items-center gap-2 md:flex">{navLinks}</div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCommandOpen(true)}
                title="命令面板"
                aria-label="打开命令面板"
                className="inline-flex h-8 w-8 items-center justify-center rounded-md text-ink-500 transition-colors hover:bg-ink-900/5 hover:text-ink-900 dark:text-[#9aa19b] dark:hover:bg-white/5 dark:hover:text-[#e6e8e3]"
              >
                <Search className="h-4 w-4" />
              </button>
              {syncingCount > 0 && (
                <NavLink
                  to="/sync-runs"
                  className="inline-flex h-8 items-center gap-1.5 rounded-md border border-brand-200 bg-brand-50 px-2.5 text-xs font-medium text-brand-700 transition-colors hover:bg-brand-100 dark:border-brand-800 dark:bg-brand-950/40 dark:text-brand-200 dark:hover:bg-brand-950/70"
                  aria-label={`${syncingCount} 个账号同步中`}
                >
                  <span className="h-3 w-3 animate-spin rounded-full border-[1.5px] border-brand-500 border-t-transparent" aria-hidden />
                  <span className="tabular-nums">{syncingCount} 同步中</span>
                </NavLink>
              )}
              <Button
                size="sm"
                loading={syncAll.isPending}
                disabled={!hasAccounts}
                onClick={() => syncAll.mutate()}
                title={hasAccounts ? "同步全部已绑定账号" : "请先添加账号"}
              >
                <RefreshCw className="h-3.5 w-3.5" aria-hidden />
                <span className="hidden sm:inline">同步</span>
              </Button>
              <button
                onClick={toggle}
                className="inline-flex h-8 w-8 items-center justify-center rounded-md text-ink-500 transition-colors hover:bg-ink-900/5 hover:text-ink-900 dark:text-[#9aa19b] dark:hover:bg-white/5 dark:hover:text-[#e6e8e3]"
                aria-label="切换主题"
              >
                {theme === "dark" ? (
                  <Sun className="h-4 w-4" />
                ) : (
                  <Moon className="h-4 w-4" />
                )}
              </button>
              <button
                onClick={() => setMobileNavOpen(true)}
                className="inline-flex h-8 w-8 items-center justify-center rounded-md text-ink-500 hover:bg-ink-900/5 md:hidden dark:text-[#9aa19b] dark:hover:bg-white/5"
                aria-label="打开导航"
              >
                <Menu className="h-5 w-5" />
              </button>
            </div>
          </div>
        </header>

        {mobileNavOpen && (
          <div className="fixed inset-0 z-40 md:hidden">
            <div
              className="absolute inset-0 bg-ink-900/30 backdrop-blur-sm"
              onClick={() => setMobileNavOpen(false)}
            />
            <div className="absolute inset-y-0 left-0 flex w-64 flex-col bg-cream-100 p-4 shadow-xl dark:bg-[#171b16]">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold">导航</span>
                <button
                  onClick={() => setMobileNavOpen(false)}
                  className="rounded-md p-1.5 text-ink-500 hover:bg-ink-900/5"
                  aria-label="关闭导航"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="mt-4 flex flex-col gap-1">{navLinks}</div>
            </div>
          </div>
        )}

        <main className="mx-auto max-w-6xl px-5 py-8 md:px-8 md:py-10">
          <div key={location.pathname} className="animate-fade-in">
            <ErrorBoundary>
              <Outlet />
            </ErrorBoundary>
          </div>
        </main>

        <footer className="mx-auto max-w-6xl px-5 pb-10 pt-4 md:px-8">
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-ink-900/8 pt-5 text-xs text-ink-500 dark:border-white/10 dark:text-[#9aa19b]">
            <span>CreatorPulse · 本地优先，数据不上传</span>
            <span className="inline-flex items-center gap-1.5">
              <span
                className={clsx(
                  "inline-flex h-1.5 w-1.5 rounded-full",
                  connected ? "bg-accent-green" : "bg-accent-amber",
                )}
                aria-hidden
              />
              仅本机 {settings.data?.host ?? "127.0.0.1"}
              {connected ? " · 实时连接正常" : " · 实时连接重连中…"}
            </span>
          </div>
        </footer>
      </div>
      <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)} />
    </div>
  );
}
