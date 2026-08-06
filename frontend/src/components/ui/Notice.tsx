import clsx from "clsx";
import type { ReactNode } from "react";
import { X } from "lucide-react";

type Tone = "info" | "success" | "warn" | "danger";

const toneClass: Record<Tone, string> = {
  info: "border-sky-200 bg-sky-50 text-sky-900 dark:border-sky-900/60 dark:bg-sky-950/40 dark:text-sky-200",
  success:
    "border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-200",
  warn: "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-200",
  danger:
    "border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-200",
};

/** Inline feedback strip shared by all pages (replaces ad-hoc message Cards). */
export function Notice({
  tone = "info",
  children,
  onDismiss,
}: {
  tone?: Tone;
  children: ReactNode;
  onDismiss?: () => void;
}) {
  return (
    <div
      role="status"
      className={clsx(
        "flex flex-wrap items-center gap-2 rounded-lg border px-4 py-2.5 text-sm",
        toneClass[tone],
      )}
    >
      <span className="min-w-0 flex-1">{children}</span>
      {onDismiss && (
        <button
          type="button"
          aria-label="关闭提示"
          onClick={onDismiss}
          className="shrink-0 rounded px-1.5 py-0.5 text-xs opacity-70 hover:opacity-100"
        >
          <X className="h-3.5 w-3.5" aria-hidden />
        </button>
      )}
    </div>
  );
}
