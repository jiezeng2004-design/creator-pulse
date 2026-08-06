import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { MetricTrendChart } from "@/components/posts/MetricTrendChart";

export function PostMetricTrendPanel({ postId }: { postId: number }) {
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["post-metrics", postId],
    queryFn: () => api.postMetrics(postId),
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <div className="py-8 text-center text-sm text-ink-500 dark:text-[#9aa19b]">
        正在加载指标趋势…
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-3 py-5 text-sm text-rose-600">
        <span>趋势加载失败：{(error as Error).message}</span>
        <button
          type="button"
          className="rounded-md border border-rose-300 px-3 py-1 text-xs hover:bg-rose-50 dark:border-rose-800 dark:hover:bg-rose-950"
          disabled={isFetching}
          onClick={() => void refetch()}
        >
          {isFetching ? "重试中…" : "重试"}
        </button>
      </div>
    );
  }

  return <MetricTrendChart snapshots={data ?? []} />;
}
