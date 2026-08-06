import { useState } from "react";
import type { MetricSnapshot } from "@/types";
import { formatDate, formatMetric } from "@/lib/format";

type MetricKey =
  | "view_count"
  | "impression_count"
  | "like_count"
  | "favorite_count"
  | "share_count"
  | "repost_count"
  | "comment_count";

const METRICS: ReadonlyArray<{ key: MetricKey; label: string }> = [
  { key: "view_count", label: "浏览" },
  { key: "impression_count", label: "曝光" },
  { key: "like_count", label: "点赞" },
  { key: "favorite_count", label: "收藏" },
  { key: "share_count", label: "分享" },
  { key: "repost_count", label: "转发" },
  { key: "comment_count", label: "评论" },
];

const WIDTH = 720;
const HEIGHT = 220;
const PADDING = { top: 16, right: 18, bottom: 30, left: 58 };

type ChartPoint = {
  snapshot: MetricSnapshot;
  value: number;
  x: number;
  y: number;
};

type ChartData = {
  points: ChartPoint[];
  segments: ChartPoint[][];
  maxValue: number;
};

function availableMetrics(snapshots: MetricSnapshot[]) {
  return METRICS.filter(({ key }) =>
    snapshots.some((snapshot) => snapshot[key] !== null),
  );
}

function buildChartData(
  snapshots: MetricSnapshot[],
  metric: MetricKey,
): ChartData {
  const dated = snapshots
    .map((snapshot) => ({
      snapshot,
      time: new Date(snapshot.captured_at).getTime(),
    }))
    .filter(({ time }) => !Number.isNaN(time))
    .sort((a, b) => a.time - b.time);
  const values = dated.flatMap(({ snapshot }) => {
    const value = snapshot[metric];
    return value === null ? [] : [value];
  });
  if (dated.length === 0 || values.length === 0) {
    return { points: [], segments: [], maxValue: 1 };
  }

  const times = dated.map((point) => point.time);
  const minTime = Math.min(...times);
  const maxTime = Math.max(...times);
  const maxValue = Math.max(...values, 1);
  const innerWidth = WIDTH - PADDING.left - PADDING.right;
  const innerHeight = HEIGHT - PADDING.top - PADDING.bottom;

  const points: ChartPoint[] = [];
  const segments: ChartPoint[][] = [];
  let segment: ChartPoint[] = [];
  dated.forEach(({ snapshot, time }) => {
    const value = snapshot[metric];
    if (value === null) {
      if (segment.length) segments.push(segment);
      segment = [];
      return;
    }
    const point = {
      snapshot,
      value,
      x:
        maxTime === minTime
          ? PADDING.left + innerWidth / 2
          : PADDING.left +
            ((time - minTime) / (maxTime - minTime)) * innerWidth,
      y: PADDING.top + innerHeight - (value / maxValue) * innerHeight,
    };
    points.push(point);
    segment.push(point);
  });
  if (segment.length) segments.push(segment);
  return { points, segments, maxValue };
}

function formatAxisMetric(value: number): string {
  if (value >= 100_000_000) return `${(value / 100_000_000).toFixed(1)}亿`;
  if (value >= 10_000) return `${(value / 10_000).toFixed(1)}万`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
  return String(Math.round(value));
}

function formatDelta(value: number): string {
  if (value === 0) return "0";
  return `${value > 0 ? "+" : ""}${value.toLocaleString("zh-CN")}`;
}

export function MetricTrendChart({
  snapshots,
}: {
  snapshots: MetricSnapshot[];
}) {
  const [selectedMetric, setSelectedMetric] = useState<MetricKey | null>(null);
  const metrics = availableMetrics(snapshots);
  const metric = metrics.some(({ key }) => key === selectedMetric)
    ? selectedMetric!
    : metrics[0]?.key;

  if (snapshots.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-ink-900/15 px-4 py-8 text-center text-sm text-ink-500 dark:border-white/15 dark:text-[#9aa19b]">
        暂无历史快照。完成两次及以上同步后，这里会显示指标变化趋势。
      </div>
    );
  }

  if (!metric) {
    return (
      <div className="rounded-lg border border-dashed border-ink-900/15 px-4 py-8 text-center text-sm text-ink-500 dark:border-white/15 dark:text-[#9aa19b]">
        该平台尚未提供可绘制的指标。
      </div>
    );
  }

  const { points, segments, maxValue } = buildChartData(snapshots, metric);
  const first = points[0];
  const latest = points[points.length - 1];
  const metricLabel =
    METRICS.find(({ key }) => key === metric)?.label ?? metric;
  const baselineY = HEIGHT - PADDING.bottom;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink-900 dark:text-[#e6e8e3]">
            指标趋势
          </h3>
          <p className="text-xs text-ink-500 dark:text-[#9aa19b]">
            按同步快照展示；缺失值不会按 0 计算
          </p>
        </div>
        <label className="flex items-center gap-2 text-xs text-ink-500 dark:text-[#9aa19b]">
          指标
          <select
            aria-label="趋势指标"
            className="rounded-md border border-ink-900/15 bg-white px-2 py-1 text-sm text-ink-900 dark:border-white/15 dark:bg-[#1a1e19] dark:text-[#e6e8e3]"
            value={metric}
            onChange={(event) =>
              setSelectedMetric(event.target.value as MetricKey)
            }
          >
            {metrics.map(({ key, label }) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid grid-cols-3 gap-2 text-sm">
        <div className="rounded-lg bg-cream-50 px-3 py-2 dark:bg-white/5">
          <div className="text-xs text-ink-500 dark:text-[#9aa19b]">最新{metricLabel}</div>
          <div className="font-semibold">{formatMetric(latest?.value)}</div>
        </div>
        <div className="rounded-lg bg-cream-50 px-3 py-2 dark:bg-white/5">
          <div className="text-xs text-ink-500 dark:text-[#9aa19b]">区间变化</div>
          <div className="font-semibold">
            {first && latest ? formatDelta(latest.value - first.value) : "—"}
          </div>
        </div>
        <div className="rounded-lg bg-cream-50 px-3 py-2 dark:bg-white/5">
          <div className="text-xs text-ink-500 dark:text-[#9aa19b]">有效快照</div>
          <div className="font-semibold">{points.length} 个</div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <svg
          className="h-auto w-full min-w-[560px] text-ink-500 dark:text-[#9aa19b]"
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          role="img"
          aria-label={`${metricLabel}历史趋势，共 ${points.length} 个有效快照`}
        >
          {[0, 0.5, 1].map((ratio) => {
            const y =
              PADDING.top + (HEIGHT - PADDING.top - PADDING.bottom) * ratio;
            const value = maxValue * (1 - ratio);
            return (
              <g key={ratio}>
                <line
                  x1={PADDING.left}
                  x2={WIDTH - PADDING.right}
                  y1={y}
                  y2={y}
                  stroke="currentColor"
                  strokeOpacity="0.18"
                />
                <text
                  x={PADDING.left - 8}
                  y={y + 4}
                  textAnchor="end"
                  fontSize="11"
                  fill="currentColor"
                >
                  {formatAxisMetric(value)}
                </text>
              </g>
            );
          })}
          <line
            x1={PADDING.left}
            x2={WIDTH - PADDING.right}
            y1={baselineY}
            y2={baselineY}
            stroke="currentColor"
            strokeOpacity="0.35"
          />
          {segments.map((segment) =>
            segment.length > 1 ? (
              <polyline
                key={segment.map((point) => point.snapshot.id).join("-")}
                points={segment
                  .map((point) => `${point.x},${point.y}`)
                  .join(" ")}
                fill="none"
                stroke="#2f4fd0"
                strokeWidth="3"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            ) : null,
          )}
          {points.map((point) => (
            <circle
              key={point.snapshot.id}
              cx={point.x}
              cy={point.y}
              r="4"
              fill="#2f4fd0"
            >
              <title>
                {formatDate(point.snapshot.captured_at)}：
                {formatMetric(point.value)}
              </title>
            </circle>
          ))}
          {first && (
            <text
              x={PADDING.left}
              y={HEIGHT - 7}
              fontSize="11"
              fill="currentColor"
            >
              {formatDate(first.snapshot.captured_at)}
            </text>
          )}
          {latest && points.length > 1 && (
            <text
              x={WIDTH - PADDING.right}
              y={HEIGHT - 7}
              textAnchor="end"
              fontSize="11"
              fill="currentColor"
            >
              {formatDate(latest.snapshot.captured_at)}
            </text>
          )}
        </svg>
      </div>
    </div>
  );
}
