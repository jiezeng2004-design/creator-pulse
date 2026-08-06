import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

/**
 * Catches render-time errors (including failed lazy-chunk loads) and shows a
 * recoverable screen instead of blanking the whole app.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: unknown): void {
    console.error("[CreatorPulse] render error:", error);
  }

  private reset = (): void => {
    this.setState({ hasError: false });
  };

  render(): ReactNode {
    if (!this.state.hasError) return this.props.children;
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center gap-4 px-5 text-center">
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-ink-900 font-mono text-[13px] font-semibold text-cream-100 dark:bg-[#e6e8e3] dark:text-[#121512]">
          CP
        </div>
        <h2 className="text-lg font-semibold tracking-tight">页面出错了</h2>
        <p className="text-sm text-ink-500 dark:text-[#9aa19b]">
          某个页面模块加载或渲染失败。可以尝试重新加载该页面，或刷新整个应用。
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={this.reset}
            className="rounded-md bg-ink-900 px-3 py-1.5 text-sm font-medium text-cream-100 hover:opacity-90 dark:bg-[#e6e8e3] dark:text-[#121512]"
          >
            重试
          </button>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="rounded-md border border-ink-900/15 px-3 py-1.5 text-sm text-ink-600 hover:bg-ink-900/5 dark:border-white/15 dark:text-[#c6cac2]"
          >
            刷新应用
          </button>
        </div>
      </div>
    );
  }
}
