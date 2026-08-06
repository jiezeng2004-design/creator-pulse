import { Link } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowUpRight,
  CalendarDays,
  Eye,
  Heart,
  Inbox,
  MessageSquarePlus,
  PlugZap,
  RefreshCw,
  Users,
} from "lucide-react";
import { api } from "@/api/client";
import { useInvalidateAll } from "@/hooks/useInvalidateAll";
import { useSyncEvents } from "@/hooks/useSyncEvents";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { MetricValue } from "@/components/ui/MetricValue";
import { StatCard } from "@/components/ui/StatCard";
import { PlatformIcon } from "@/components/platform/PlatformIcon";
import {
  PHASE_LABEL,
  PLATFORM_LABEL,
  STATUS_LABEL,
  relativeTime,
  statusTone,
} from "@/lib/format";
import { platformColor } from "@/lib/platforms";

const PHASE_ORDER = [
  "queued",
  "checking_auth",
  "fetching_profile",
  "fetching_posts",
  "fetching_metrics",
  "fetching_comments",
  "done",
];

function phaseIndex(phase: string | null | undefined): number {
  const idx = PHASE_ORDER.indexOf(phase || "");
  return idx === -1 ? 0 : idx;
}

export function DashboardPage() {
  const invalidateAll = useInvalidateAll();
  const { progress } = useSyncEvents();
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["dashboard"],
    queryFn: api.dashboard,
  });
  const accounts = useQuery({
    queryKey: ["accounts"],
    queryFn: api.accounts,
    staleTime: 2_000,
  });
  const recentRuns = useQuery({
    queryKey: ["sync-runs", "recent"],
    queryFn: () => api.syncRuns({ page: 1, page_size: 5 }),
    staleTime: 10_000,
  });

  const syncAll = useMutation({
    mutationFn: api.syncAll,
    onSuccess: () => invalidateAll(),
  });

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 w-48 rounded bg-ink-900/8 dark:bg-white/10" />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-28 rounded-lg bg-ink-900/8 dark:bg-white/10" />
          ))}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="h-56 rounded-lg bg-ink-900/8 dark:bg-white/10" />
          <div className="h-56 rounded-lg bg-ink-900/8 dark:bg-white/10" />
        </div>
      </div>
    );
  }
  if (error || !data) {
    return (
      <div className="text-rose-600">
        加载失败：{(error as Error)?.message || "未知错误"}
        <button className="ml-2 underline" onClick={() => refetch()}>重试</button>
      </div>
    );
  }

  const noAccounts = data.platforms.every((p) => p.account_count === 0);
  const hasConnected = accounts.data?.some((a) => a.account_status === "connected") ?? false;
  const livePlatformCount = new Set(
    Object.keys(progress).map((id) => accounts.data?.find((a) => a.id === Number(id))?.platform),
  ).size;

  const needsLogin = (accounts.data ?? []).filter(
    (a) =>
      a.account_status === "login_required" ||
      a.next_action?.action === "login" ||
      a.next_action?.action === "check_auth",
  );
  const needsLoginPlatforms = [
    ...new Set(needsLogin.map((a) => PLATFORM_LABEL[a.platform] || a.platform)),
  ];
  const runs = recentRuns.data?.items ?? [];

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-5">
        <div>
          <div className="mb-3 font-mono text-[11px] font-medium uppercase tracking-[0.18em] text-ink-500 dark:text-[#9aa19b]">
            01 / 运营索引
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-semibold tracking-[-0.03em] text-ink-900 dark:text-[#e6e8e3]">
              运营总览
            </h1>
            {data.mock_mode && <Badge tone="mock">演示数据</Badge>}
          </div>
          <p className="mt-3 max-w-xl text-sm leading-6 text-ink-500 dark:text-[#9aa19b]">
            把分散的平台信号整理成可核验的内容、触达与互动状态。缺失指标保持为空，不用 0 代替未知。
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="mr-2 text-xs text-ink-400 dark:text-[#9aa19b]">
            {livePlatformCount > 0
              ? `${livePlatformCount} 个平台同步中`
              : `最近成功同步 ${relativeTime(data.last_global_sync_at)}`}
          </span>
          <Button
            size="sm"
            loading={syncAll.isPending}
            disabled={noAccounts}
            onClick={() => syncAll.mutate()}
          >
            <RefreshCw className="h-3.5 w-3.5" aria-hidden />
            同步全部
          </Button>
          <Link to="/accounts">
            <Button size="sm" variant="secondary">管理账号</Button>
          </Link>
        </div>
      </header>

      {syncAll.isSuccess && (
        <div className="border-l-2 border-brand-600 bg-brand-50 px-4 py-3 text-sm text-brand-800 dark:bg-brand-950/30 dark:text-brand-200">
          已加入后台队列 {syncAll.data.started} 个
          {syncAll.data.skipped > 0 ? `，跳过 ${syncAll.data.skipped} 个正在同步的账号` : ""}。
          <Link className="ml-2 underline underline-offset-2" to="/sync-runs">查看同步记录</Link>
        </div>
      )}

      {needsLogin.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 dark:border-amber-900/60 dark:bg-amber-950/30">
          <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300">
            <AlertTriangle className="h-4 w-4" aria-hidden />
          </span>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-medium text-amber-900 dark:text-amber-100">
              {needsLogin.length} 个账号需要登录（{needsLoginPlatforms.join("、")}）
            </div>
            <div className="text-xs text-amber-700 dark:text-amber-300/80">
              打开登录并手动完成验证后，点击「检查并同步」即可开始拉取数据。
            </div>
          </div>
          <Link to="/accounts">
            <Button size="sm" variant="secondary">
              去处理
              <ArrowUpRight className="h-3.5 w-3.5" aria-hidden />
            </Button>
          </Link>
        </div>
      )}

      <section aria-label="关键指标">
        <div className="mb-3 flex items-center justify-between">
          <div className="font-mono text-[11px] font-medium uppercase tracking-[0.18em] text-ink-500 dark:text-[#9aa19b]">
            02 / 当前信号
          </div>
          <span className="text-xs text-ink-400">数据范围：本地已同步内容</span>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="近 24h 发文" value={data.posts_last_24h} icon={CalendarDays} tone="info" hint="今日新发布内容数" />
          <StatCard label="近 7 天发文" value={data.posts_last_7d} icon={CalendarDays} hint="近一周发布内容数" />
          <StatCard label="总浏览 / 曝光" value={data.total_views_or_impressions} icon={Eye} hint="仅统计平台已提供的指标" />
          <StatCard label="总互动" value={data.total_engagement} icon={Heart} hint="赞同、点赞、收藏、转发、评论" />
        </div>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <StatCard
            label="新评论"
            value={data.new_comments}
            icon={MessageSquarePlus}
            tone="info"
            hint="尚未处理的平台新评论"
          />
          <StatCard
            label="待处理评论"
            value={data.pending_comments}
            icon={Inbox}
            tone={data.pending_comments > 0 ? "warn" : "success"}
            hint={data.pending_comments > 0 ? "建议优先处理" : "收件箱已清空"}
          />
        </div>
      </section>

      <section>
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="mb-2 font-mono text-[11px] font-medium uppercase tracking-[0.18em] text-ink-500 dark:text-[#9aa19b]">
              03 / 平台工作台
            </div>
            <h2 className="text-xl font-semibold tracking-tight md:text-2xl">按平台查看真实信号</h2>
          </div>
          <span className="text-xs text-ink-400">指标不可用时显示“暂不可用”，不代表为 0</span>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          {data.platforms.map((p, index) => {
            const platformAccounts = accounts.data?.filter((a) => a.platform === p.platform) ?? [];
            const liveAccount = platformAccounts.find((a) => progress[a.id]);
            const liveProgress = liveAccount ? progress[liveAccount.id] : undefined;
            const displayStatus = liveProgress ? "同步中" : p.status_summary;
            const color = platformColor(p.platform);
            return (
              <Card key={p.platform} hoverable className="group overflow-hidden p-0 animate-fade-in">
                <div className="h-1 w-full" style={{ backgroundColor: color }} aria-hidden />
                <div className="flex flex-wrap items-start justify-between gap-4 px-5 py-5 md:px-6">
                  <div className="flex min-w-0 items-center gap-3">
                    <PlatformIcon platform={p.platform} size="lg" />
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="text-lg font-semibold tracking-tight">{p.platform_label}</h3>
                        <Badge tone={platformStatusTone(liveProgress ? "同步中" : p.status_summary)} dot>{displayStatus}</Badge>
                      </div>
                      <p className="mt-1 text-xs text-ink-500 dark:text-[#9aa19b]">
                        {p.account_count} 个账号 · {p.experimental ? "实验性适配" : "标准适配"}
                        {p.is_mock ? " · 演示数据" : ""}
                      </p>
                    </div>
                  </div>
                  <span className="font-mono text-[11px] text-ink-400">{String(index + 1).padStart(2, "0")}</span>
                </div>
                <div className="grid grid-cols-2 divide-x divide-y divide-ink-900/8 px-5 py-5 sm:grid-cols-4 sm:divide-y-0 md:px-6 dark:divide-white/10">
                  <MetricBlock label="近 7 天内容" value={p.posts_last_7d} />
                  <MetricBlock label={p.metric_primary_label} value={p.metric_primary_value} />
                  <MetricBlock label={p.metric_secondary_label} value={p.metric_secondary_value} />
                  <MetricBlock label={p.metric_tertiary_label} value={p.metric_tertiary_value} />
                </div>
                {liveProgress && (
                  <div className="px-5 pb-4 md:px-6">
                    <div className="mb-1.5 flex items-center justify-between text-xs">
                      <span className="font-medium text-brand-600 dark:text-brand-300">
                        {PHASE_LABEL[liveProgress.phase] || "同步中"}
                      </span>
                      <span className="tabular-nums text-ink-400">
                        内容 {liveProgress.posts_fetched ?? 0} · 评论 {liveProgress.comments_fetched ?? 0}
                      </span>
                    </div>
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-900/5 dark:bg-white/10">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-brand-500 to-brand-600 transition-all duration-500"
                        style={{
                          width: `${Math.max(
                            10,
                            ((phaseIndex(liveProgress.phase) + 1) / PHASE_ORDER.length) * 100,
                          )}%`,
                        }}
                      />
                    </div>
                  </div>
                )}
                <div className="flex flex-wrap items-center justify-between gap-3 border-t border-ink-900/8 px-5 py-4 text-xs md:px-6 dark:border-white/10">
                  <div className="min-w-0 text-ink-500 dark:text-[#9aa19b]">
                    <span className="text-ink-400">最近成功同步：</span>
                    <span className={liveProgress ? "font-medium text-brand-600 dark:text-brand-300" : ""}>
                      {liveProgress ? PHASE_LABEL[liveProgress.phase] || "同步中" : relativeTime(p.last_sync_at)}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 whitespace-nowrap">
                    <Link className="inline-flex items-center gap-1 text-ink-600 hover:text-brand-600 dark:text-[#c6cac2]" to={`/posts?platform=${p.platform}`}>
                      内容 <ArrowUpRight className="h-3.5 w-3.5" aria-hidden />
                    </Link>
                    <Link className="inline-flex items-center gap-1 text-ink-600 hover:text-brand-600 dark:text-[#c6cac2]" to={`/comments?platform=${p.platform}`}>
                      评论 <ArrowUpRight className="h-3.5 w-3.5" aria-hidden />
                    </Link>
                  </div>
                </div>
                {p.metric_note && (
                  <div className="border-t border-dashed border-ink-900/10 px-5 py-3 text-[11px] leading-5 text-ink-400 md:px-6 dark:border-white/10 dark:text-[#9aa19b]">
                    {p.metric_note}
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      </section>

      {runs.length > 0 && (
        <section>
          <div className="mb-3 flex items-center justify-between">
            <div className="font-mono text-[11px] font-medium uppercase tracking-[0.18em] text-ink-500 dark:text-[#9aa19b]">
              04 / 最近动态
            </div>
            <Link className="text-xs text-brand-600 hover:underline dark:text-brand-300" to="/sync-runs">
              全部记录
            </Link>
          </div>
          <Card className="divide-y divide-ink-900/8 p-0 dark:divide-white/10">
            {runs.map((r) => (
              <div key={r.id} className="flex flex-wrap items-center gap-3 px-5 py-3 text-sm md:px-6">
                <span
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ backgroundColor: platformColor(r.platform) }}
                  aria-hidden
                />
                <span className="min-w-0 flex-1 truncate font-medium">
                  {PLATFORM_LABEL[r.platform] || r.platform} · {r.account_display_name}
                </span>
                <span className="tabular-nums text-xs text-ink-400">
                  内容 {r.posts_fetched} · 评论 {r.comments_fetched}
                </span>
                <Badge
                  dot
                  tone={r.status === "success" ? "success" : r.status === "failed" ? "danger" : "warn"}
                >
                  {STATUS_LABEL[r.status] || r.status}
                </Badge>
                <span className="text-xs text-ink-400">{relativeTime(r.finished_at || r.started_at)}</span>
              </div>
            ))}
          </Card>
        </section>
      )}

      {noAccounts && (
        <EmptyState
          title="还没有连接任何账号"
          description="两步即可开始：添加账号 → 登录/配置 Token → 一键同步。也可先用演示数据熟悉界面。"
          icon={Users}
          actions={[{ label: "去连接账号", to: "/accounts", primary: true }, { label: "打开设置（演示数据）", to: "/settings" }]}
        />
      )}

      {!noAccounts && !hasConnected && (
        <EmptyState
          title="账号已添加，但尚未完成登录"
          description="国内平台：打开登录并手动完成验证；X：配置 Bearer Token 后检查连接。完成后用「同步全部」。"
          icon={PlugZap}
          actions={[{ label: "去账号管理", to: "/accounts", primary: true }]}
        />
      )}
    </div>
  );
}

function MetricBlock({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="min-w-0 px-3 first:pl-0 last:pr-0 md:px-5">
      <div className="truncate text-[11px] text-ink-400 dark:text-[#9aa19b]">{label}</div>
      <div className="mt-2 truncate text-lg font-semibold tabular-nums text-ink-900 dark:text-[#e6e8e3]"><MetricValue value={value} compact /></div>
    </div>
  );
}

function platformStatusTone(status: string) {
  if (status === "已连接") return statusTone("connected");
  if (status === "同步中") return statusTone("syncing");
  if (status === "异常") return statusTone("error");
  if (status === "需要登录" || status === "未连接") return statusTone("needs_login");
  return statusTone(status);
}
