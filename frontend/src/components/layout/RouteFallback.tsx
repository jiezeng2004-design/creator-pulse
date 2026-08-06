export function RouteFallback() {
  return (
    <div className="space-y-6 animate-pulse" aria-busy="true" aria-label="页面加载中">
      <div className="h-8 w-48 rounded bg-ink-900/8 dark:bg-white/10" />
      <div className="h-64 rounded-xl bg-ink-900/8 dark:bg-white/10" />
    </div>
  );
}
