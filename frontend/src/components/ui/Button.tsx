import clsx from "clsx";
import { Loader2 } from "lucide-react";

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md";
  loading?: boolean;
};

export function Button({
  className,
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  children,
  ...props
}: Props) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center gap-1.5 rounded-md font-medium transition-all duration-150",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40 focus-visible:ring-offset-1 focus-visible:ring-offset-cream-100 dark:focus-visible:ring-offset-[#121512]",
        "disabled:cursor-not-allowed disabled:opacity-50 active:scale-[0.98]",
        size === "sm" && "px-2.5 py-1 text-xs",
        size === "md" && "px-3.5 py-2 text-sm",
        variant === "primary" &&
          "bg-brand-600 text-white shadow-sm hover:bg-brand-700 dark:bg-brand-500 dark:text-[#0d173f] dark:hover:bg-brand-400",
        variant === "secondary" &&
          "border border-ink-900/15 bg-white text-ink-700 shadow-sm hover:border-brand-500/40 hover:text-brand-700 dark:border-white/15 dark:bg-white/5 dark:text-[#c6cac2] dark:hover:border-white/30 dark:hover:text-white",
        variant === "danger" &&
          "bg-rose-600 text-white hover:bg-rose-700",
        variant === "ghost" &&
          "text-ink-500 hover:bg-ink-900/5 hover:text-ink-900 dark:text-[#9aa19b] dark:hover:bg-white/5 dark:hover:text-white",
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />}
      {children}
    </button>
  );
}
