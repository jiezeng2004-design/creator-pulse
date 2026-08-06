import { useQueryClient } from "@tanstack/react-query";

const ALL_QUERY_KEYS = [
  "accounts",
  "dashboard",
  "posts",
  "comments",
  "sync-runs",
  "settings",
  "platforms",
] as const;

export function useInvalidateAll() {
  const qc = useQueryClient();
  return () => {
    for (const key of ALL_QUERY_KEYS) {
      qc.invalidateQueries({ queryKey: [key] });
    }
  };
}
