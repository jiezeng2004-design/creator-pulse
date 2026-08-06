import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  CornerDownLeft,
  FileText,
  LayoutDashboard,
  MessageSquare,
  Moon,
  Plus,
  RefreshCw,
  Search,
  Settings,
  Sun,
  Users,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import clsx from "clsx";
import { api } from "@/api/client";
import { useInvalidateAll } from "@/hooks/useInvalidateAll";
import { PLATFORMS } from "@/lib/platforms";
import { useTheme } from "@/lib/theme";

type Command = {
  id: string;
  group: string;
  label: string;
  keywords: string;
  icon: LucideIcon;
  action: () => void;
};

export function CommandPalette({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  const { theme, toggle } = useTheme();
  const invalidateAll = useInvalidateAll();
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  const syncAll = useMutation({
    mutationFn: api.syncAll,
    onSuccess: () => invalidateAll(),
  });

  const commands = useMemo<Command[]>(() => {
    const go = (to: string) => () => {
      navigate(to);
      onClose();
    };
    const list: Command[] = [
      {
        id: "nav-dashboard",
        group: "页面",
        label: "运营总览",
        keywords: "总览 首页 dashboard",
        icon: LayoutDashboard,
        action: go("/"),
      },
      {
        id: "nav-posts",
        group: "页面",
        label: "内容列表",
        keywords: "内容 帖子 posts",
        icon: FileText,
        action: go("/posts"),
      },
      {
        id: "nav-comments",
        group: "页面",
        label: "评论收件箱",
        keywords: "评论 收件箱 comments",
        icon: MessageSquare,
        action: go("/comments"),
      },
      {
        id: "nav-accounts",
        group: "页面",
        label: "账号管理",
        keywords: "账号 绑定 登录 accounts",
        icon: Users,
        action: go("/accounts"),
      },
      {
        id: "nav-sync-runs",
        group: "页面",
        label: "同步记录",
        keywords: "同步 记录 日志 sync",
        icon: RefreshCw,
        action: go("/sync-runs"),
      },
      {
        id: "nav-settings",
        group: "页面",
        label: "设置",
        keywords: "设置 配置 token 备份 settings",
        icon: Settings,
        action: go("/settings"),
      },
    ];
    for (const p of PLATFORMS) {
      list.push({
        id: `posts-${p.id}`,
        group: "平台快捷",
        label: `${p.label} · 查看内容`,
        keywords: `${p.label} 内容 posts ${p.id}`,
        icon: FileText,
        action: go(`/posts?platform=${p.id}`),
      });
      list.push({
        id: `comments-${p.id}`,
        group: "平台快捷",
        label: `${p.label} · 查看评论`,
        keywords: `${p.label} 评论 comments ${p.id}`,
        icon: MessageSquare,
        action: go(`/comments?platform=${p.id}`),
      });
    }
    list.push(
      {
        id: "action-add-account",
        group: "操作",
        label: "添加账号",
        keywords: "添加 新增 绑定 登录",
        icon: Plus,
        action: go("/accounts"),
      },
      {
        id: "action-sync-all",
        group: "操作",
        label: "同步全部账号",
        keywords: "同步 全部 刷新 refresh",
        icon: RefreshCw,
        action: () => {
          syncAll.mutate();
          onClose();
        },
      },
      {
        id: "action-theme",
        group: "操作",
        label: theme === "dark" ? "切换到浅色主题" : "切换到深色主题",
        keywords: "主题 深色 浅色 夜间 theme",
        icon: theme === "dark" ? Sun : Moon,
        action: () => {
          toggle();
          onClose();
        },
      },
      {
        id: "action-export",
        group: "操作",
        label: "导出数据备份",
        keywords: "导出 备份 数据库 export",
        icon: Settings,
        action: go("/settings"),
      },
    );
    return list;
    // syncAll.mutate is stable; command set depends on theme only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navigate, onClose, theme, toggle]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return commands;
    return commands.filter((c) =>
      `${c.label} ${c.keywords} ${c.group}`.toLowerCase().includes(q),
    );
  }, [commands, query]);

  useEffect(() => {
    if (open) {
      setQuery("");
      setActive(0);
      window.setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [open]);

  useEffect(() => {
    setActive(0);
  }, [query]);

  useEffect(() => {
    const el = listRef.current?.querySelector<HTMLElement>(`[data-index="${active}"]`);
    el?.scrollIntoView?.({ block: "nearest" });
  }, [active]);

  if (!open) return null;

  const run = (command: Command) => command.action();

  const onDialogKeyDown = (e: React.KeyboardEvent) => {
    if (e.key !== "Tab") return;
    const focusables = dialogRef.current?.querySelectorAll<HTMLElement>(
      'button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])',
    );
    if (!focusables || focusables.length === 0) return;
    const first = focusables.item(0);
    const last = focusables.item(focusables.length - 1);
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  };

  return (
    <div
      ref={dialogRef}
      className="fixed inset-0 z-50 flex items-start justify-center px-4 pt-[12vh]"
      role="dialog"
      aria-modal="true"
      aria-label="命令面板"
      onKeyDown={onDialogKeyDown}
    >
      <button
        type="button"
        aria-label="关闭命令面板"
        className="absolute inset-0 cursor-default bg-ink-900/40 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative w-full max-w-xl overflow-hidden rounded-xl border border-ink-900/10 bg-white shadow-2xl animate-fade-in dark:border-white/10 dark:bg-[#171b16]">
        <div className="flex items-center gap-2.5 border-b border-ink-900/8 px-4 dark:border-white/10">
          <Search className="h-4 w-4 shrink-0 text-ink-400" aria-hidden />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索页面、平台或操作…"
            className="h-12 min-w-0 flex-1 border-0 bg-transparent text-sm text-ink-900 outline-none placeholder:text-ink-400 dark:text-[#e6e8e3] dark:placeholder:text-[#7a807b]"
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setActive((a) => Math.min(a + 1, filtered.length - 1));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setActive((a) => Math.max(a - 1, 0));
              } else if (e.key === "Enter") {
                const target = filtered[active];
                if (target) {
                  e.preventDefault();
                  run(target);
                }
              } else if (e.key === "Escape") {
                e.preventDefault();
                onClose();
              }
            }}
          />
          <button
            type="button"
            onClick={onClose}
            aria-label="关闭"
            className="rounded-md p-1.5 text-ink-400 transition-colors hover:bg-ink-900/5 hover:text-ink-900 dark:hover:bg-white/5 dark:hover:text-white"
          >
            <X className="h-4 w-4" aria-hidden />
          </button>
        </div>

        <div ref={listRef} className="max-h-[50vh] overflow-y-auto p-2">
          {filtered.length === 0 && (
            <div className="px-4 py-10 text-center text-sm text-ink-400 dark:text-[#9aa19b]">
              没有匹配的结果
            </div>
          )}
          {filtered.map((command, index) => {
            const previous = filtered[index - 1];
            const firstInGroup = !previous || previous.group !== command.group;
            const Icon = command.icon;
            return (
              <div key={command.id}>
                {firstInGroup && (
                  <div className="px-3 pb-1.5 pt-3 text-[11px] font-medium uppercase tracking-wider text-ink-400 first:pt-1.5 dark:text-[#7a807b]">
                    {command.group}
                  </div>
                )}
                <button
                  type="button"
                  data-index={index}
                  onMouseEnter={() => setActive(index)}
                  onClick={() => run(command)}
                  className={clsx(
                    "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition-colors",
                    index === active
                      ? "bg-brand-50 text-brand-900 dark:bg-brand-950/50 dark:text-brand-100"
                      : "text-ink-700 dark:text-[#c6cac2]",
                  )}
                >
                  <Icon
                    className={clsx(
                      "h-4 w-4 shrink-0",
                      index === active
                        ? "text-brand-600 dark:text-brand-300"
                        : "text-ink-400",
                    )}
                    aria-hidden
                  />
                  <span className="min-w-0 flex-1 truncate">{command.label}</span>
                  {index === active && (
                    <ArrowRight className="h-3.5 w-3.5 shrink-0 opacity-70" aria-hidden />
                  )}
                </button>
              </div>
            );
          })}
        </div>

        <div className="flex items-center gap-3 border-t border-ink-900/8 px-4 py-2.5 text-[11px] text-ink-400 dark:border-white/10 dark:text-[#7a807b]">
          <span className="inline-flex items-center gap-1">
            <ArrowUp className="h-3 w-3" aria-hidden />
            <ArrowDown className="h-3 w-3" aria-hidden />
          </span>
          <CornerDownLeft className="h-3 w-3" aria-hidden />
          <X className="h-3 w-3" aria-hidden />
        </div>
      </div>
    </div>
  );
}
