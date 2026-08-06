import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Check,
  CheckCheck,
  Clock,
  Copy,
  EyeOff,
  ExternalLink,
  Inbox,
  MessageSquare,
  MessageSquarePlus,
} from "lucide-react";
import { api } from "@/api/client";
import { useDebounce } from "@/hooks/useDebounce";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Notice } from "@/components/ui/Notice";
import { Pagination } from "@/components/ui/Pagination";
import { CardListSkeleton } from "@/components/ui/Skeleton";
import { PageHeader } from "@/components/layout/PageHeader";
import { PLATFORM_LABEL, STATUS_LABEL, formatDate, statusTone } from "@/lib/format";
import { STATUS_TABS, PLATFORMS } from "@/lib/platforms";
import { platformColor } from "@/lib/platforms";

const STATUS_ICONS = {
  "": Inbox,
  new: MessageSquarePlus,
  pending: Clock,
  handled: CheckCheck,
  ignored: EyeOff,
} as const;

export function CommentsPage() {
  const [params, setParams] = useSearchParams();
  const [status, setStatus] = useState(params.get("status") || "");
  const [platform, setPlatform] = useState(params.get("platform") || "");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const qc = useQueryClient();
  const debouncedSearch = useDebounce(search, 300);
  const [msg, setMsg] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["comments", status, platform, debouncedSearch, page],
    queryFn: () =>
      api.comments({
        page,
        page_size: 20,
        local_status: status || undefined,
        platform: platform || undefined,
        search: debouncedSearch || undefined,
      }),
  });

  const mutation = useMutation({
    mutationFn: ({ id, local_status }: { id: number; local_status: string }) =>
      api.updateCommentStatus(id, local_status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["comments"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (e: Error) => setMsg(`操作失败：${e.message}`),
  });

  const batchMutation = useMutation({
    mutationFn: ({ ids, local_status }: { ids: number[]; local_status: string }) =>
      api.batchUpdateCommentStatus(ids, local_status),
    onSuccess: (res) => {
      setSelected(new Set());
      qc.invalidateQueries({ queryKey: ["comments"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      setMsg(`已批量更新 ${res.updated} 条评论 → ${STATUS_LABEL[res.status] || res.status}`);
    },
    onError: (e: Error) => setMsg(`批量操作失败：${e.message}`),
  });
  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };
  const allOnPageSelected =
    !!data && data.items.length > 0 && data.items.every((c) => selected.has(c.id));
  const toggleSelectAllPage = () => {
    if (!data) return;
    setSelected((prev) => {
      const next = new Set(prev);
      if (allOnPageSelected) {
        for (const c of data.items) next.delete(c.id);
      } else {
        for (const c of data.items) next.add(c.id);
      }
      return next;
    });
  };

  const copyContent = (id: number, content: string) => {
    void navigator.clipboard.writeText(content);
    setCopiedId(id);
    window.setTimeout(() => setCopiedId((cur) => (cur === id ? null : cur)), 1500);
  };

  return (
    <div className="space-y-8">
      <PageHeader
        kicker="03 / 互动处理"
        title="评论收件箱"
        description="本地处理状态（new/pending/handled/ignored），不会在平台自动回复，请跳转原平台处理。"
      />

      <section aria-label="评论筛选">
        <div className="mb-3 flex items-center justify-between">
          <div className="font-mono text-[11px] font-medium uppercase tracking-[0.18em] text-ink-500 dark:text-[#9aa19b]">
            评论流
          </div>
          <span className="text-xs text-ink-400">本地处理状态，不自动回复</span>
        </div>
        <Card className="flex flex-wrap items-center gap-3 p-4">
          <div className="flex flex-wrap items-center gap-2">
            {STATUS_TABS.map((t) => (
              <StatusTab
                key={t.value}
                label={t.label}
                active={status === t.value}
                icon={STATUS_ICONS[t.value as keyof typeof STATUS_ICONS]}
                onClick={() => {
                  setPage(1);
                  setStatus(t.value);
                  const next = new URLSearchParams(params);
                  if (t.value) next.set("status", t.value);
                  else next.delete("status");
                  setParams(next, { replace: true });
                }}
              />
            ))}
          </div>
          <div className="mx-1 hidden h-6 w-px bg-ink-900/10 sm:block dark:bg-white/10" aria-hidden />
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => {
                setPage(1);
                setPlatform("");
                const next = new URLSearchParams(params);
                next.delete("platform");
                setParams(next, { replace: true });
              }}
              className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                platform === ""
                  ? "bg-ink-900 text-white dark:bg-[#e6e8e3] dark:text-[#121512]"
                  : "bg-ink-900/5 text-ink-600 hover:bg-ink-900/10 dark:bg-white/10 dark:text-[#c6cac2] dark:hover:bg-white/15"
              }`}
            >
              全部平台
            </button>
            {PLATFORMS.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => {
                  setPage(1);
                  setPlatform(p.id);
                  const next = new URLSearchParams(params);
                  next.set("platform", p.id);
                  setParams(next, { replace: true });
                }}
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                  platform === p.id
                    ? "bg-ink-900 text-white dark:bg-[#e6e8e3] dark:text-[#121512]"
                    : "bg-ink-900/5 text-ink-600 hover:bg-ink-900/10 dark:bg-white/10 dark:text-[#c6cac2] dark:hover:bg-white/15"
                }`}
              >
                <span
                  className="h-1.5 w-1.5 rounded-full"
                  style={{ backgroundColor: platform === p.id ? "currentColor" : platformColor(p.id) }}
                  aria-hidden
                />
                {p.label}
              </button>
            ))}
          </div>
          <input
            className="min-w-[200px] flex-1 rounded-md border border-ink-900/15 bg-transparent px-2 py-1.5 text-sm dark:border-white/15"
            placeholder="搜索评论内容 / 作者"
            value={search}
            onChange={(e) => {
              setPage(1);
              setSearch(e.target.value);
            }}
          />
          {data && data.total > 0 && (
            <span className="whitespace-nowrap text-xs tabular-nums text-ink-400">
              共 {data.total} 条
            </span>
          )}
        </Card>
      </section>
      {msg && (
        <Notice tone="info" onDismiss={() => setMsg("")}>
          {msg}
        </Notice>
      )}

      {isLoading && <CardListSkeleton rows={4} />}
      {error && (
        <Notice tone="danger">加载失败：{(error as Error).message}</Notice>
      )}

      {data && data.total === 0 && (
        <EmptyState
          title="暂无评论"
          description="同步账号后会聚合各平台评论。本地状态（待处理/已处理）不会伪装成平台官方已回复。"
          icon={MessageSquare}
          actions={[
            { label: "去同步账号", to: "/accounts", primary: true },
            { label: "看内容列表", to: "/posts" },
          ]}
        />
      )}

      <section aria-label="评论列表">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="mb-2 font-mono text-[11px] font-medium uppercase tracking-[0.18em] text-ink-500 dark:text-[#9aa19b]">
              评论列表
            </div>
            <h2 className="text-xl font-semibold tracking-tight md:text-2xl">
              {status
                ? STATUS_TABS.find((t) => t.value === status)?.label || "评论列表"
                : "全部评论"}
            </h2>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {data && data.total > 0 && (
              <p className="text-xs text-ink-400 dark:text-[#9aa19b]">
                单篇最多同步 100 条样本，以平台页面为准
              </p>
            )}
            <label className="flex cursor-pointer items-center gap-2 text-xs font-medium text-ink-600 dark:text-[#9aa19b]">
              <input
                type="checkbox"
                checked={allOnPageSelected}
                onChange={toggleSelectAllPage}
                className="h-4 w-4"
              />
              全选本页（{data?.items.length ?? 0} 条）
            </label>
          </div>
        </div>

        {selected.size > 0 && (
          <div className="mb-4 flex flex-wrap items-center gap-2 rounded-lg border border-ink-900/10 bg-white px-4 py-3 shadow-card dark:border-white/10 dark:bg-[#1a1e19]">
            <span className="text-sm font-medium">已选 {selected.size} 条</span>
            <Button
              size="sm"
              variant="secondary"
              loading={batchMutation.isPending}
              onClick={() =>
                batchMutation.mutate({
                  ids: [...selected],
                  local_status: "handled",
                })
              }
            >
              <CheckCheck className="h-3.5 w-3.5" aria-hidden />
              批量标记已处理
            </Button>
            <Button
              size="sm"
              variant="secondary"
              loading={batchMutation.isPending}
              onClick={() =>
                batchMutation.mutate({
                  ids: [...selected],
                  local_status: "pending",
                })
              }
            >
              <Clock className="h-3.5 w-3.5" aria-hidden />
              批量标记待处理
            </Button>
            <Button
              size="sm"
              variant="ghost"
              loading={batchMutation.isPending}
              onClick={() =>
                batchMutation.mutate({
                  ids: [...selected],
                  local_status: "ignored",
                })
              }
            >
              <EyeOff className="h-3.5 w-3.5" aria-hidden />
              批量忽略
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setSelected(new Set())}>
              取消选择
            </Button>
          </div>
        )}

        <div className="space-y-3">
          {data?.items.map((c) => (
            <Card
              key={c.id}
              hoverable
              className={`overflow-hidden p-0 animate-fade-in ${
                selected.has(c.id) ? "ring-2 ring-brand-300 dark:ring-brand-700" : ""
              }`}
            >
              <div
                className="h-1 w-full"
                style={{ backgroundColor: platformColor(c.platform || "") }}
                aria-hidden
              />
              <div className="flex flex-wrap items-start justify-between gap-3 px-5 py-5">
                <div className="flex min-w-0 flex-1 items-start gap-3">
                  <input
                    type="checkbox"
                    aria-label={`选择评论 ${c.id}`}
                    checked={selected.has(c.id)}
                    onChange={() => toggleSelect(c.id)}
                    className="mt-1 h-4 w-4 shrink-0"
                  />
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2 text-sm">
                      <span className="font-medium">{c.author_name || "匿名"}</span>
                      <Badge>{PLATFORM_LABEL[c.platform || ""] || c.platform}</Badge>
                      <Badge tone={statusTone(c.local_status)}>
                        {STATUS_LABEL[c.local_status] || c.local_status}
                      </Badge>
                      {c.replied_by_owner && <Badge tone="success">平台检测到已回复</Badge>}
                    </div>
                    <div className="text-sm leading-relaxed break-words">{c.content}</div>
                    <div className="text-xs text-ink-500">
                      所属内容：{c.post_title || `#${c.post_id}`} · {formatDate(c.published_at)}
                    </div>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    loading={mutation.isPending}
                    onClick={() => mutation.mutate({ id: c.id, local_status: "pending" })}
                  >
                    待处理
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    loading={mutation.isPending}
                    onClick={() => mutation.mutate({ id: c.id, local_status: "handled" })}
                  >
                    已处理
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    loading={mutation.isPending}
                    onClick={() => mutation.mutate({ id: c.id, local_status: "ignored" })}
                  >
                    忽略
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => copyContent(c.id, c.content)}
                  >
                    {copiedId === c.id ? (
                      <>
                        <Check className="h-3.5 w-3.5" aria-hidden /> 已复制
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5" aria-hidden /> 复制
                      </>
                    )}
                  </Button>
                  {c.comment_url && (
                    <a href={c.comment_url} target="_blank" rel="noreferrer">
                      <Button size="sm" variant="primary">
                        <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                        打开原平台
                      </Button>
                    </a>
                  )}
                  {!c.comment_url && c.post_url && (
                    <a href={c.post_url} target="_blank" rel="noreferrer">
                      <Button size="sm" variant="primary">
                        <ExternalLink className="h-3.5 w-3.5" aria-hidden />
                        打开内容
                      </Button>
                    </a>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      </section>

      {data && data.total > 0 && (
        <Pagination
          page={data.page}
          pageSize={data.page_size}
          total={data.total}
          onChange={setPage}
        />
      )}
    </div>
  );
}

function StatusTab({
  label,
  active,
  icon: Icon,
  onClick,
}: {
  label: string;
  active: boolean;
  icon: typeof Inbox;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
        active
          ? "bg-ink-900 text-white shadow-sm dark:bg-[#e6e8e3] dark:text-[#121512]"
          : "bg-ink-900/5 text-ink-700 hover:bg-ink-900/10 dark:bg-white/10 dark:text-[#c6cac2] dark:hover:bg-white/15"
      }`}
    >
      <Icon className="h-3.5 w-3.5" aria-hidden />
      {label}
    </button>
  );
}
