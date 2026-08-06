import clsx from "clsx";

export function Badge({
  children,
  tone = "default",
  dot = false,
}: {
  children: React.ReactNode;
  tone?: "default" | "success" | "warn" | "danger" | "info" | "mock";
  dot?: boolean;
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 text-xs font-medium",
        tone === "default" &&
          "text-ink-600 dark:text-[#c6cac2]",
        tone === "success" &&
          "text-accent-green dark:text-[#4fb393]",
        tone === "warn" &&
          "text-accent-amber dark:text-[#e0a64e]",
        tone === "danger" &&
          "text-accent-rose dark:text-[#e26b8a]",
        tone === "info" &&
          "text-brand-600 dark:text-[#8aa0e6]",
        tone === "mock" &&
          "text-[#7c3aed] dark:text-[#b9a0ef]",
      )}
    >
      {dot && (
        <span
          className={clsx(
            "h-1.5 w-1.5 shrink-0 rounded-full",
            tone === "success" && "bg-accent-green",
            tone === "warn" && "bg-accent-amber",
            tone === "danger" && "bg-accent-rose",
            tone === "info" && "bg-brand-500",
            tone === "mock" && "bg-[#7c3aed]",
            tone === "default" && "bg-ink-400",
          )}
          aria-hidden
        />
      )}
      {children}
    </span>
  );
}
