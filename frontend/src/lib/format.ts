export function formatMetric(value: number | null | undefined): string {
  if (value === null || value === undefined) return "暂不可用";
  return value.toLocaleString("zh-CN");
}

/** Compact metric for dense tables: 12.4k, 1.2万 for zh audiences when large. */
export function formatMetricCompact(value: number | null | undefined): string {
  if (value === null || value === undefined) return "暂不可用";
  if (value >= 100_000_000) return `${(value / 100_000_000).toFixed(1)}亿`;
  if (value >= 10_000) return `${(value / 10_000).toFixed(1)}万`;
  if (value >= 1000) return value.toLocaleString("zh-CN");
  return String(value);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString("zh-CN");
  } catch {
    return value;
  }
}

export function relativeTime(value: string | null | undefined): string {
  if (!value) return "从未同步";
  const t = new Date(value).getTime();
  if (Number.isNaN(t)) return "—";
  const diff = Date.now() - t;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "刚刚";
  if (mins < 60) return `${mins} 分钟前`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  return `${days} 天前`;
}

export { PLATFORM_LABEL, PLATFORM_ACCENT } from "./platforms";

export const STATUS_LABEL: Record<string, string> = {
  new: "新评论",
  pending: "待处理",
  handled: "已处理",
  ignored: "已忽略",
  connected: "已连接",
  disconnected: "未连接",
  login_required: "需要登录",
  syncing: "同步中",
  error: "异常",
  rate_limited: "限流",
  success: "成功",
  failed: "失败",
  partial: "部分成功",
  cancelled: "已取消",
  queued: "排队中",
  running: "运行中",
};

/** Coarse sync phase labels shared by accounts / sync-runs pages. */
export const PHASE_LABEL: Record<string, string> = {
  queued: "排队中",
  checking_auth: "正在检查登录状态",
  fetching_profile: "正在拉取账号资料",
  fetching_posts: "正在拉取内容",
  fetching_metrics: "正在更新指标",
  fetching_comments: "正在拉取评论",
  done: "同步完成",
};

export function statusTone(
  status: string,
): "default" | "success" | "warn" | "danger" | "info" | "mock" {
  if (["connected", "success", "handled"].includes(status)) return "success";
  if (["error", "failed", "rate_limited"].includes(status)) return "danger";
  if (
    ["login_required", "disconnected", "pending", "syncing", "queued", "running", "partial"].includes(
      status,
    )
  )
    return "warn";
  if (status === "new") return "info";
  return "default";
}
