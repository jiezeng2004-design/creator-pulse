import { Link } from "react-router-dom";
import type { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/Button";

type Action = {
  label: string;
  to?: string;
  onClick?: () => void;
  primary?: boolean;
};

export function EmptyState({
  title,
  description,
  actions = [],
  icon: Icon,
}: {
  title: string;
  description: string;
  actions?: Action[];
  icon?: LucideIcon;
}) {
  return (
    <div className="rounded-lg border border-dashed border-ink-900/15 bg-ink-900/[0.02] px-6 py-14 text-center dark:border-white/15 dark:bg-white/[0.02]">
      {Icon && (
        <div className="mx-auto mb-4 flex h-11 w-11 items-center justify-center rounded-md bg-white text-ink-400 shadow-card ring-1 ring-ink-900/10 dark:bg-[#1a1e19] dark:text-[#9aa19b] dark:ring-white/10">
          <Icon className="h-6 w-6" aria-hidden />
        </div>
      )}
      <div className="text-base font-semibold text-ink-900 dark:text-[#e6e8e3]">
        {title}
      </div>
      <p className="mx-auto mt-2 max-w-md text-sm text-ink-500 dark:text-[#9aa19b]">
        {description}
      </p>
      {actions.length > 0 && (
        <div className="mt-5 flex flex-wrap justify-center gap-2">
          {actions.map((a) =>
            a.to ? (
              <Link key={a.label} to={a.to}>
                <Button variant={a.primary ? "primary" : "secondary"} size="sm">
                  {a.label}
                </Button>
              </Link>
            ) : (
              <Button
                key={a.label}
                variant={a.primary ? "primary" : "secondary"}
                size="sm"
                onClick={a.onClick}
              >
                {a.label}
              </Button>
            ),
          )}
        </div>
      )}
    </div>
  );
}
