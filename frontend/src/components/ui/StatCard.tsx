import clsx from "clsx";
import type { LucideIcon } from "lucide-react";
import { MetricValue } from "@/components/ui/MetricValue";

export function StatCard({
  label,
  value,
  hint,
  tone = "default",
  emphasize,
  icon: Icon,
}: {
  label: string;
  value: number | null | undefined;
  hint?: string;
  tone?: "default" | "info" | "warn" | "danger" | "success";
  emphasize?: boolean;
  icon?: LucideIcon;
}) {
  return (
    <div
      className={clsx(
        "group relative overflow-hidden rounded-lg border border-ink-900/10 bg-white p-5 transition-all duration-200",
        "dark:border-white/10 dark:bg-[#1a1e19]",
        "hover:border-ink-900/20 hover:shadow-cardHover dark:hover:border-white/20",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="font-mono text-[11px] font-medium uppercase tracking-wider text-ink-500 dark:text-[#9aa19b]">
          {label}
        </div>
        {Icon && (
          <span
            className={clsx(
              "inline-flex h-6 w-6 items-center justify-center rounded-md transition-colors",
              tone === "info" && "text-brand-500 dark:text-brand-300",
              tone === "warn" && "text-accent-amber dark:text-[#e0a64e]",
              tone === "danger" && "text-accent-rose dark:text-[#e26b8a]",
              tone === "success" && "text-accent-green dark:text-[#4fb393]",
              tone === "default" && "text-ink-400 dark:text-[#9aa19b]",
            )}
          >
            <Icon className="h-4 w-4" aria-hidden />
          </span>
        )}
      </div>
      <div
        className={clsx(
          "mt-3 font-mono text-3xl font-semibold tabular-nums tracking-tight text-ink-900 dark:text-[#e6e8e3]",
          emphasize && "text-brand-600 dark:text-brand-300",
        )}
      >
        <MetricValue value={value} />
      </div>
      {hint && (
        <div className="mt-1.5 text-[11px] text-ink-400 dark:text-[#9aa19b]">
          {hint}
        </div>
      )}
    </div>
  );
}
