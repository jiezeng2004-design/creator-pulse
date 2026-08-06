import { ChevronLeft, ChevronRight } from "lucide-react";

/** Consistent pagination footer for posts / comments / sync-runs lists. */
export function Pagination({
  page,
  pageSize,
  total,
  onChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onChange: (next: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const btn =
    "inline-flex items-center gap-1 rounded-md border border-ink-900/15 px-2.5 py-1.5 text-xs " +
    "text-ink-700 transition-colors hover:border-ink-900/30 hover:text-ink-900 " +
    "disabled:cursor-not-allowed disabled:opacity-40 " +
    "dark:border-white/15 dark:text-[#c6cac2] dark:hover:border-white/30 dark:hover:text-white";
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-ink-500 dark:text-[#9aa19b]">
      <span className="tabular-nums">
        共 {total} 条 · 第 {page}/{totalPages} 页
      </span>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onChange(Math.max(1, page - 1))}
          className={btn}
        >
          <ChevronLeft className="h-3.5 w-3.5" aria-hidden />
          上一页
        </button>
        <button
          type="button"
          disabled={page >= totalPages}
          onClick={() => onChange(Math.min(totalPages, page + 1))}
          className={btn}
        >
          下一页
          <ChevronRight className="h-3.5 w-3.5" aria-hidden />
        </button>
      </div>
    </div>
  );
}
