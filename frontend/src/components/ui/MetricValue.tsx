import { formatMetric, formatMetricCompact } from "@/lib/format";
import clsx from "clsx";

export function MetricValue({
  value,
  compact = false,
  className,
}: {
  value: number | null | undefined;
  compact?: boolean;
  className?: string;
}) {
  if (value === null || value === undefined) {
    return (
      <span
        className={
          className ||
          "inline-flex items-center rounded bg-ink-900/5 px-1.5 py-0.5 font-mono text-xs font-normal text-ink-400 dark:bg-white/5 dark:text-[#9aa19b]"
        }
        title="平台未提供或尚未获取，不是 0"
      >
        暂不可用
      </span>
    );
  }
  return (
    <span
      className={clsx("font-mono tabular-nums", className)}
      title={formatMetric(value)}
    >
      {compact ? formatMetricCompact(value) : formatMetric(value)}
    </span>
  );
}
