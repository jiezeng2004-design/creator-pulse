import clsx from "clsx";

export function Card({
  children,
  className,
  hoverable = false,
  style,
}: {
  children: React.ReactNode;
  className?: string;
  hoverable?: boolean;
  style?: React.CSSProperties;
}) {
  return (
    <div
      style={style}
      className={clsx(
        "rounded-lg border border-ink-900/10 bg-white shadow-card transition-all duration-200 dark:border-white/10 dark:bg-[#1a1e19]",
        hoverable &&
          "hover:border-ink-900/20 hover:shadow-cardHover dark:hover:border-white/20",
        className,
      )}
    >
      {children}
    </div>
  );
}
