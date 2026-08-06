import clsx from "clsx";

/** Neutral pulsing placeholder block for loading states. */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={clsx(
        "animate-pulse rounded-md bg-ink-900/8 dark:bg-white/10",
        className,
      )}
    />
  );
}

/** Skeleton shaped like a Card row list (accounts / sync runs / comments). */
export function CardListSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3" role="status" aria-label="加载中">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="rounded-lg border border-ink-900/10 bg-white p-5 dark:border-white/10 dark:bg-[#1a1e19]"
        >
          <Skeleton className="h-4 w-52" />
          <Skeleton className="mt-3 h-3 w-72 max-w-full" />
          <Skeleton className="mt-2 h-3 w-40" />
        </div>
      ))}
    </div>
  );
}

/** Skeleton shaped like a dense table (posts). */
export function TableSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div
      className="overflow-hidden rounded-lg border border-ink-900/10 bg-white dark:border-white/10 dark:bg-[#1a1e19]"
      role="status"
      aria-label="加载中"
    >
      <div className="border-b border-ink-900/10 bg-cream-50/80 px-3 py-2.5 dark:border-white/10 dark:bg-[#121512]/80">
        <Skeleton className="h-3 w-full max-w-md" />
      </div>
      <div className="space-y-0">
        {Array.from({ length: rows }).map((_, i) => (
          <div
            key={i}
            className="flex items-center gap-4 border-b border-ink-900/8 px-3 py-3 last:border-b-0 dark:border-white/10"
          >
            <Skeleton className="h-3 w-14 shrink-0" />
            <Skeleton className="h-3 flex-1" />
            <Skeleton className="h-3 w-24 shrink-0" />
            <Skeleton className="hidden h-3 w-16 shrink-0 sm:block" />
          </div>
        ))}
      </div>
    </div>
  );
}
