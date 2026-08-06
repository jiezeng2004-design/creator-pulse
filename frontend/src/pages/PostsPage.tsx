import { Fragment, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowDown,
  ArrowUp,
  ChevronDown,
  Copy,
  FileText,
  LineChart,
} from "lucide-react";
import clsx from "clsx";
import { api } from "@/api/client";
import { useDebounce } from "@/hooks/useDebounce";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { MetricValue } from "@/components/ui/MetricValue";
import { Notice } from "@/components/ui/Notice";
import { Pagination } from "@/components/ui/Pagination";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { PageHeader } from "@/components/layout/PageHeader";
import { PLATFORM_LABEL, formatDate } from "@/lib/format";
import { PLATFORMS, platformColor } from "@/lib/platforms";
import { PostMetricTrendPanel } from "@/components/posts/PostMetricTrendPanel";

export function PostsPage() {
  const [params, setParams] = useSearchParams();
  const [platform, setPlatform] = useState(params.get("platform") || "");
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("published_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [expandedPostId, setExpandedPostId] = useState<number | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const debouncedSearch = useDebounce(search, 300);

  const { data, isLoading, error } = useQuery({
    queryKey: ["posts", platform, debouncedSearch, sortBy, sortDir, page],
    queryFn: () =>
      api.posts({
        page,
        page_size: 20,
        platform: platform || undefined,
        search: debouncedSearch || undefined,
        sort_by: sortBy,
        sort_dir: sortDir,
      }),
  });

  const setSort = (key: string) => {
    setPage(1);
    if (key === sortBy) {
      setSortDir((dir) => (dir === "desc" ? "asc" : "desc"));
    } else {
      setSortBy(key);
      setSortDir("desc");
    }
  };

  return (
    <div className="space-y-4">
      <PageHeader
        kicker="02 / 内容信号"
        title="内容列表"
        description="聚合各平台内容与指标，缺失指标显示「暂不可用」。"
      />

      <Card className="space-y-3 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setPage(1);
              setPlatform("");
              const next = new URLSearchParams(params);
              next.delete("platform");
              setParams(next, { replace: true });
            }}
            className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
              platform === ""
                ? "bg-ink-900 text-white dark:bg-[#e6e8e3] dark:text-[#121512]"
                : "bg-ink-900/5 text-ink-600 hover:bg-ink-900/10 dark:bg-white/10 dark:text-[#c6cac2] dark:hover:bg-white/15"
            }`}
          >
            全部平台
          </button>
          {PLATFORMS.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => {
                setPage(1);
                setPlatform(p.id);
                const next = new URLSearchParams(params);
                next.set("platform", p.id);
                setParams(next, { replace: true });
              }}
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                platform === p.id
                  ? "bg-ink-900 text-white dark:bg-[#e6e8e3] dark:text-[#121512]"
                  : "bg-ink-900/5 text-ink-600 hover:bg-ink-900/10 dark:bg-white/10 dark:text-[#c6cac2] dark:hover:bg-white/15"
              }`}
            >
              <span
                className="h-1.5 w-1.5 rounded-full"
                style={{ backgroundColor: platform === p.id ? "currentColor" : platformColor(p.id) }}
                aria-hidden
              />
              {p.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <input
            className="min-w-[200px] flex-1 rounded-md border border-ink-900/15 bg-transparent px-2 py-1.5 text-sm dark:border-white/15"
            placeholder="搜索标题…"
            value={search}
            onChange={(e) => {
              setPage(1);
              setSearch(e.target.value);
            }}
          />
          {data && data.total > 0 && (
            <span className="whitespace-nowrap text-xs tabular-nums text-ink-400">
              共 {data.total} 条
            </span>
          )}
        </div>
      </Card>

      {isLoading && <TableSkeleton rows={8} />}
      {error && (
        <Notice tone="danger">加载失败：{(error as Error).message}</Notice>
      )}

      {data && data.total === 0 && (
        <EmptyState
          title="暂无内容"
          description="连接账号并完成「检查并同步」后，这里会显示标题、浏览/点赞等指标。缺失指标显示「暂不可用」。"
          icon={FileText}
          actions={[
            { label: "去账号管理", to: "/accounts", primary: true },
            { label: "返回总览", to: "/" },
          ]}
        />
      )}

      {data && data.total > 0 && (
        <Card className="p-0">
          {/* Table scrolls horizontally on narrow screens; pagination stays
              outside the scroll region so it never scrolls off-screen. */}
          <div className="overflow-x-auto">
            <table className="table-fixed w-full text-left text-sm">
            <thead className="border-b border-ink-900/10 bg-cream-50/80 text-xs text-ink-500 dark:border-white/10 dark:bg-[#121512]/80">
              <tr>
                <th className="w-14 px-3 py-2.5 font-mono text-[11px] font-medium uppercase tracking-wider">平台</th>
                <th className="w-96 max-w-96 px-3 py-2.5 font-mono text-[11px] font-medium uppercase tracking-wider">标题</th>
                <SortHeader label="发布时间" sortKey="published_at" active={sortBy === "published_at"} dir={sortDir} onSort={setSort} className="hidden w-32 lg:table-cell" />
                <SortHeader label="浏览" sortKey="view_count" active={sortBy === "view_count"} dir={sortDir} onSort={setSort} className="w-16" />
                <SortHeader label="曝光" sortKey="impression_count" active={sortBy === "impression_count"} dir={sortDir} onSort={setSort} className="hidden w-16 xl:table-cell" />
                <SortHeader label="点赞" sortKey="like_count" active={sortBy === "like_count"} dir={sortDir} onSort={setSort} className="w-16" />
                <th className="hidden w-16 px-3 py-2.5 font-mono text-[11px] font-medium uppercase tracking-wider md:table-cell">收藏</th>
                <th className="hidden w-16 px-3 py-2.5 font-mono text-[11px] font-medium uppercase tracking-wider xl:table-cell">转发</th>
                <SortHeader label="评论" sortKey="comment_count" active={sortBy === "comment_count"} dir={sortDir} onSort={setSort} className="w-16" />
                <th className="hidden w-28 px-3 py-2.5 font-mono text-[11px] font-medium uppercase tracking-wider xl:table-cell">最近同步</th>
                <th className="w-24 px-3 py-2.5 font-mono text-[11px] font-medium uppercase tracking-wider">趋势</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((p) => (
                <Fragment key={p.id}>
                  <tr className="border-b border-ink-900/8 transition-colors hover:bg-cream-50/60 dark:border-white/10 dark:hover:bg-ink-900/40">
                    <td className="px-3 py-2">
                      <Badge>
                        <span
                          className="inline-block h-1.5 w-1.5 rounded-full"
                          style={{ backgroundColor: platformColor(p.platform || "") }}
                          aria-hidden
                        />
                        {PLATFORM_LABEL[p.platform || ""] || p.platform}
                      </Badge>
                    </td>
                    <td className="overflow-hidden px-3 py-2">
                      <div className="flex min-w-0 items-center gap-1.5">
                        {p.post_url ? (
                          <a
                            href={p.post_url}
                            target="_blank"
                            rel="noreferrer"
                            className="min-w-0 truncate text-brand-600 hover:underline"
                          >
                            {p.title || p.content_preview || p.platform_post_id}
                          </a>
                        ) : (
                          <span className="min-w-0 truncate">
                            {p.title || p.content_preview || p.platform_post_id}
                          </span>
                        )}
                        {p.post_url && (
                          <button
                            type="button"
                            title="复制链接"
                            aria-label="复制链接"
                            onClick={() => {
                              void navigator.clipboard.writeText(p.post_url!);
                              setCopiedId(p.id);
                              window.setTimeout(
                                () => setCopiedId((cur) => (cur === p.id ? null : cur)),
                                1500,
                              );
                            }}
                            className="shrink-0 rounded p-1 text-ink-400 transition-colors hover:bg-ink-900/5 hover:text-ink-700 dark:hover:bg-white/10 dark:hover:text-white"
                          >
                            <Copy className={`h-3.5 w-3.5 ${copiedId === p.id ? "text-brand-600 dark:text-brand-300" : ""}`} aria-hidden />
                          </button>
                        )}
                      </div>
                    </td>
                    <td className="hidden px-3 py-2 whitespace-nowrap lg:table-cell">
                      {formatDate(p.published_at)}
                    </td>
                    <td className="px-3 py-2">
                      <MetricValue value={p.view_count} />
                    </td>
                    <td className="hidden px-3 py-2 xl:table-cell">
                      <MetricValue value={p.impression_count} />
                    </td>
                    <td className="px-3 py-2">
                      <MetricValue value={p.like_count} />
                    </td>
                    <td className="hidden px-3 py-2 md:table-cell">
                      <MetricValue value={p.favorite_count} />
                    </td>
                    <td className="hidden px-3 py-2 xl:table-cell">
                      <MetricValue value={p.repost_count ?? p.share_count} />
                    </td>
                    <td className="px-3 py-2">
                      <MetricValue value={p.comment_count} />
                    </td>
                    <td className="hidden px-3 py-2 whitespace-nowrap xl:table-cell">
                      {formatDate(p.metrics_updated_at)}
                    </td>
                    <td className="px-3 py-2">
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 whitespace-nowrap rounded-md px-2 py-1 text-xs font-medium text-brand-600 transition-colors hover:bg-brand-50 dark:text-brand-500 dark:hover:bg-white/10"
                        aria-expanded={expandedPostId === p.id}
                        aria-controls={`post-trend-${p.id}`}
                        onClick={() =>
                          setExpandedPostId((current) =>
                            current === p.id ? null : p.id,
                          )
                        }
                      >
                        <LineChart className="h-3.5 w-3.5" aria-hidden />
                        {expandedPostId === p.id ? "收起" : "趋势"}
                        <ChevronDown
                          className={`h-3 w-3 transition-transform ${expandedPostId === p.id ? "rotate-180" : ""}`}
                          aria-hidden
                        />
                      </button>
                    </td>
                  </tr>
                  {expandedPostId === p.id && (
                    <tr
                      id={`post-trend-${p.id}`}
                      className="bg-cream-50/70 dark:bg-[#121512]/50"
                    >
                      <td colSpan={11} className="px-4 py-4">
                        <PostMetricTrendPanel postId={p.id} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
          </div>
          <div className="px-3 py-2.5">
            <Pagination
              page={data.page}
              pageSize={data.page_size}
              total={data.total}
              onChange={setPage}
            />
          </div>
        </Card>
      )}
    </div>
  );
}

function SortHeader({
  label,
  sortKey,
  active,
  dir,
  onSort,
  className,
}: {
  label: string;
  sortKey: string;
  active: boolean;
  dir: "asc" | "desc";
  onSort: (key: string) => void;
  className?: string;
}) {
  const Icon = active && dir === "asc" ? ArrowUp : ArrowDown;
  return (
    <th className={clsx("px-3 py-2.5", className)}>
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        aria-label={`按${label}排序`}
        className={clsx(
          "inline-flex items-center gap-0.5 rounded font-mono text-[11px] font-medium uppercase tracking-wider transition-colors",
          active
            ? "text-brand-600 dark:text-brand-300"
            : "text-ink-500 hover:text-ink-900 dark:text-[#9aa19b] dark:hover:text-[#e6e8e3]",
        )}
      >
        {label}
        <Icon
          className={clsx("h-3 w-3", !active && "opacity-30")}
          aria-hidden
        />
      </button>
    </th>
  );
}
