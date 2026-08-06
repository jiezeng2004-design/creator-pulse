import { useQuery } from "@tanstack/react-query";
import {
  CheckCircle2,
  Clock,
  Loader2,
  RefreshCw,
  Timer,
  XCircle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { api } from "@/api/client";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Notice } from "@/components/ui/Notice";
import { CardListSkeleton } from "@/components/ui/Skeleton";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  PHASE_LABEL,
  PLATFORM_LABEL,
  STATUS_LABEL,
  formatDate,
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

function phaseIndex(phase: string | null): number {
  const idx = PHASE_ORDER.indexOf(phase || "");
  return idx === -1 ? 0 : idx;
}

function statusMeta(
  status: string,
): { icon: LucideIcon; tone: "success" | "danger" | "warn" | "default"; label: string } {
  if (status === "success") return { icon: CheckCircle2, tone: "success", label: "成功" };
  if (status === "failed") return { icon: XCircle, tone: "danger", label: "失败" };
  if (status === "cancelled") return { icon: Clock, tone: "warn", label: "已取消" };
  return { icon: Loader2, tone: "warn", label: "运行中" };
}

function durationLabel(startedAt: string, finishedAt: string | null): string {
  const start = new Date(startedAt).getTime();
  const end = finishedAt ? new Date(finishedAt).getTime() : Date.now();
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) return "—";
  const seconds = Math.round((end - start) / 1000);
  if (seconds < 60) return `${seconds} 秒`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes} 分 ${seconds % 60} 秒`;
}

export function SyncRunsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["sync-runs"],
    queryFn: () => api.syncRuns({ page: 1, page_size: 50 }),
    // SSE events invalidate this query instantly; the interval is only a
    // fallback in case the event stream is unavailable.
    refetchInterval: 30_000,
  });

  return (
    <div className="space-y-4">
      <PageHeader
        kicker="05 / 运行轨迹"
        title="同步记录"
        description="同步进度通过实时推送即时更新（兜底 30 秒自动刷新）；诊断信息已脱敏，不会显示 Cookie / Token。"
      />
      {data && data.items.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-3">
          <RunSummary label="最近记录" value={data.total} hint="本页展示最近 50 条" tone="info" icon={RefreshCw} />
          <RunSummary
            label="成功"
            value={data.items.filter((r) => r.status === "success").length}
            tone="success"
            icon={CheckCircle2}
          />
          <RunSummary
            label="失败 / 运行中"
            value={data.items.filter((r) => r.status === "failed" || r.status === "queued" || r.status === "running").length}
            tone={data.items.some((r) => r.status === "failed") ? "danger" : "info"}
            icon={XCircle}
          />
        </div>
      )}
      {isLoading && <CardListSkeleton rows={4} />}
      {error && (
        <Notice tone="danger">加载失败：{(error as Error).message}</Notice>
      )}
      {data && data.total === 0 && (
        <Card className="border-dashed py-12 text-center">
          <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-lg bg-ink-900/5 text-ink-400 dark:bg-white/10">
            <RefreshCw className="h-5 w-5" aria-hidden />
          </div>
          <div className="text-sm text-ink-500">暂无同步记录</div>
          <div className="mt-1 text-xs text-ink-400">触发一次账号同步后，这里会显示进度与结果。</div>
        </Card>
      )}
      <div className="space-y-3">
        {data?.items.map((r) => (
          <Card key={r.id} className="animate-fade-in p-5">
            <div className="flex flex-wrap items-center gap-2.5 text-sm">
              <span
                className="h-2 w-2 shrink-0 rounded-full"
                style={{ backgroundColor: platformColor(r.platform) }}
                aria-hidden
              />
              <span className="font-medium">
                {PLATFORM_LABEL[r.platform] || r.platform} · {r.account_display_name}
              </span>
              <Badge dot tone={statusMeta(r.status).tone}>
                {STATUS_LABEL[r.status] || r.status}
              </Badge>
              <Badge>{r.sync_type}</Badge>
              <span className="ml-auto inline-flex items-center gap-1.5 text-xs tabular-nums text-ink-400">
                <Timer className="h-3.5 w-3.5" aria-hidden />
                {durationLabel(r.started_at, r.finished_at)}
              </span>
            </div>
            <div className="mt-3 grid gap-2 text-xs text-ink-500 sm:grid-cols-2 dark:text-[#9aa19b]">
              <div className="flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-ink-400" aria-hidden />
                开始：{formatDate(r.started_at)}
              </div>
              <div className="flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-ink-400" aria-hidden />
                结束：{formatDate(r.finished_at)}
              </div>
              {["queued", "running"].includes(r.status) && (
                <div className="sm:col-span-2">
                  <div className="mb-1.5 flex items-center justify-between text-xs">
                    <span className="text-brand-600 dark:text-brand-400">
                      阶段：{PHASE_LABEL[r.phase || ""] || "准备中"}
                    </span>
                    <span className="text-ink-400">
                      第 {phaseIndex(r.phase) + 1}/{PHASE_ORDER.length} 步
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-900/5 dark:bg-white/10">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-brand-500 to-brand-600 transition-all duration-500"
                      style={{
                        width: `${Math.max(
                          12,
                          ((phaseIndex(r.phase) + 1) / PHASE_ORDER.length) * 100,
                        )}%`,
                      }}
                    />
                  </div>
                </div>
              )}
              <div>获取内容：<span className="tabular-nums">{r.posts_fetched}</span></div>
              <div>获取评论：<span className="tabular-nums">{r.comments_fetched}</span></div>
              {r.error_code && <div>错误码：{r.error_code}</div>}
              {r.error_message && <div className="text-rose-600 sm:col-span-2">{r.error_message}</div>}
              {r.diagnostic && (
                <pre className="sm:col-span-2 overflow-x-auto rounded bg-cream-50 p-2 dark:bg-[#121512]">
                  {JSON.stringify(r.diagnostic, null, 2)}
                </pre>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

function RunSummary({
  label,
  value,
  hint,
  tone,
  icon: Icon,
}: {
  label: string;
  value: number;
  hint?: string;
  tone: "info" | "success" | "danger";
  icon: LucideIcon;
}) {
  return (
    <div className="rounded-lg border border-ink-900/10 bg-white p-4 shadow-card dark:border-white/10 dark:bg-[#1a1e19]">
      <div className="flex items-center justify-between gap-2 text-xs text-ink-500 dark:text-[#9aa19b]">
        <span>{label}</span>
        <Icon
          className={`h-4 w-4 ${
            tone === "info"
              ? "text-brand-600 dark:text-brand-300"
              : tone === "success"
                ? "text-accent-green"
                : "text-accent-rose"
          }`}
          aria-hidden
        />
      </div>
      <div className="mt-2 font-mono text-2xl font-semibold tabular-nums text-ink-900 dark:text-[#e6e8e3]">
        {value}
      </div>
      {hint && <div className="mt-1 text-[11px] text-ink-400 dark:text-[#9aa19b]">{hint}</div>}
    </div>
  );
}
