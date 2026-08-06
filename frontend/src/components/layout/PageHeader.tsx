import type { ReactNode } from "react";

/**
 * Unified page title block. Keeps every page's heading scale, kicker, and
 * description consistent instead of each page rolling its own markup.
 */
export function PageHeader({
  title,
  kicker,
  description,
  actions,
}: {
  title: string;
  kicker?: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-5">
      <div className="min-w-0">
        {kicker && (
          <div className="mb-3 font-mono text-[11px] font-medium uppercase tracking-[0.18em] text-ink-500 dark:text-[#9aa19b]">
            {kicker}
          </div>
        )}
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-semibold tracking-[-0.03em] text-ink-900 dark:text-[#e6e8e3]">
            {title}
          </h1>
        </div>
        {description && (
          <p className="mt-3 max-w-xl text-sm leading-6 text-ink-500 dark:text-[#9aa19b]">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}
