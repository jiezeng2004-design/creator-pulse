import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Bell,
  Database,
  ExternalLink,
  KeyRound,
  Layers,
  Save,
  Trash2,
  Upload,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { api } from "@/api/client";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Switch } from "@/components/ui/Switch";
import { Notice } from "@/components/ui/Notice";
import { Skeleton } from "@/components/ui/Skeleton";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  getNotifyEnabled,
  notificationsSupported,
  requestNotificationPermission,
  setNotifyEnabled,
} from "@/hooks/useSyncNotification";

export function SettingsPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const platforms = useQuery({ queryKey: ["platforms"], queryFn: api.platforms });
  const [notifyEnabled, setNotifyEnabledState] = useState(getNotifyEnabled());
  const [xToken, setXToken] = useState("");
  const xCred = useQuery({
    queryKey: ["x-credentials"],
    queryFn: api.xCredentials,
    staleTime: 30_000,
  });
  const [form, setForm] = useState({
    enable_scheduled_sync: false,
    sync_interval_minutes: 60,
    sync_max_posts: 50,
    data_retention_days: 365,
    dev_mode: false,
    enable_mock_data: false,
  });
  const [msg, setMsg] = useState("");

  const exportMut = useMutation({
    mutationFn: async () => {
      const res = await api.exportDatabase();
      if (!res.ok) {
        let message = "导出失败";
        try {
          const body = await res.json();
          message = body?.detail || message;
        } catch {
          /* ignore */
        }
        throw new Error(message);
      }
      const blob = await res.blob();
      const disposition = res.headers.get("content-disposition") || "";
      const filenameMatch = disposition.match(/filename="?(.+)"?$/);
      const filename = filenameMatch ? filenameMatch[1] : "creator_pulse_backup.zip";
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename || "creator_pulse_backup.zip";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    },
    onSuccess: () => setMsg("备份导出成功"),
    onError: (e: Error) => setMsg(`导出失败：${e.message}`),
  });

  const cleanupMut = useMutation({
    mutationFn: api.cleanupNow,
    onSuccess: (r) => {
      // Retention removes rows the dashboard has already counted.
      qc.invalidateQueries();
      setMsg(
        r.total_deleted === 0
          ? `没有超过 ${r.retention_days} 天的数据需要清理`
          : `已清理 ${r.total_deleted} 条：内容 ${r.posts_deleted} · 评论 ${r.comments_deleted} · 指标快照 ${r.snapshots_deleted} · 同步记录 ${r.sync_runs_deleted}`,
      );
    },
    onError: (e: Error) => setMsg(`清理失败：${e.message}`),
  });

  const saveX = useMutation({
    mutationFn: (token: string) => api.saveXCredentials(token),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["x-credentials"] });
      qc.invalidateQueries({ queryKey: ["accounts"] });
      setXToken("");
      setMsg("X Bearer Token 已保存并立即生效");
    },
    onError: (e: Error) => setMsg(`保存失败：${e.message}`),
  });

  useEffect(() => {
    if (data) {
      setForm({
        enable_scheduled_sync: data.enable_scheduled_sync,
        sync_interval_minutes: data.sync_interval_minutes,
        sync_max_posts: data.sync_max_posts,
        data_retention_days: data.data_retention_days,
        dev_mode: data.dev_mode,
        enable_mock_data: data.enable_mock_data,
      });
    }
  }, [data]);

  const save = useMutation({
    mutationFn: () => api.updateSettings(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["settings"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      setMsg("设置已保存");
    },
    onError: (e: Error) => setMsg(e.message),
  });

  if (isLoading || !data) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-40" />
        <Skeleton className="h-3 w-72 max-w-full" />
        <div className="space-y-3 pt-2">
          <Skeleton className="h-40 w-full rounded-lg" />
          <Skeleton className="h-52 w-full rounded-lg" />
          <Skeleton className="h-24 w-full rounded-lg" />
        </div>
      </div>
    );
  }

  const xConfigured = xCred.data?.configured ?? false;

  return (
    <div className="space-y-4">
      <PageHeader
        kicker="06 / 系统配置"
        title="设置"
        description="同步策略、开发开关与本地路径说明。"
      />
      {msg && (
        <Notice tone="info" onDismiss={() => setMsg("")}>
          {msg}
        </Notice>
      )}

      <Card className="space-y-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <SectionTitle icon={Layers} title="通用设置" description="同步频率、抓取范围与数据保留策略。" />
          <Button onClick={() => save.mutate()} loading={save.isPending}>
            <Save className="h-3.5 w-3.5" aria-hidden />
            保存设置
          </Button>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <Switch
            checked={form.enable_scheduled_sync}
            onChange={(next) => setForm({ ...form, enable_scheduled_sync: next })}
            label="启用定时同步"
          />
          启用定时同步（默认关闭，最小间隔 30 分钟）
        </label>
        <label className="block text-sm">
          同步间隔（分钟）
          <input
            type="number"
            min={30}
            className="mt-1 block w-40 rounded-md border border-ink-900/15 bg-transparent px-2 py-1.5 dark:border-white/15"
            value={form.sync_interval_minutes}
            onChange={(e) =>
              setForm({ ...form, sync_interval_minutes: Number(e.target.value) })
            }
          />
        </label>
        <label className="block text-sm">
          每次同步最大帖子数
          <input
            type="number"
            min={1}
            max={200}
            className="mt-1 block w-40 rounded-md border border-ink-900/15 bg-transparent px-2 py-1.5 dark:border-white/15"
            value={form.sync_max_posts}
            onChange={(e) => setForm({ ...form, sync_max_posts: Number(e.target.value) })}
          />
        </label>
        <label className="block text-sm">
          数据保留天数
          <input
            type="number"
            min={7}
            className="mt-1 block w-40 rounded-md border border-ink-900/15 bg-transparent px-2 py-1.5 dark:border-white/15"
            value={form.data_retention_days}
            onChange={(e) =>
              setForm({ ...form, data_retention_days: Number(e.target.value) })
            }
          />
        </label>
        <label className="flex items-center gap-2 text-sm">
          <Switch
            checked={form.dev_mode}
            onChange={(next) => setForm({ ...form, dev_mode: next })}
            label="开发模式"
          />
          开发模式
        </label>
        <label className="flex items-center gap-2 text-sm">
          <Switch
            checked={form.enable_mock_data}
            onChange={(next) => setForm({ ...form, enable_mock_data: next })}
            label="全局 Mock 数据开关"
          />
          全局 Mock 数据开关
          <Badge tone="mock">演示数据</Badge>
        </label>
      </Card>

      <Card className="space-y-3 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <SectionTitle icon={KeyRound} title="X API 配置" description="网页端直接管理 Bearer Token。" />
          <Badge tone={xConfigured ? "success" : "warn"} dot>
            {xConfigured ? "已配置" : "未配置"}
          </Badge>
        </div>
        <p className="text-xs leading-relaxed text-ink-500">
          填写 X Developer Portal 生成的 <strong>Bearer Token</strong>（app-only），
          无需 Consumer Secret / Access Token。Token 仅保存在本机（
          <code className="rounded bg-ink-900/5 px-1 py-0.5 dark:bg-white/10">backend/.env.x</code>
          ，已加入 .gitignore），不会上传、不会在页面回显。保存后立即生效，无需重启。
        </p>
        <p className="text-xs leading-relaxed text-ink-500">
          还需要在「账号」添加 X 账号时填写你的 <strong>X 用户名</strong>（不含 @），
          app-only Token 需通过用户名定位账号。
        </p>
        <div className="flex flex-wrap gap-2">
          <input
            type="password"
            className="min-w-[220px] flex-1 rounded-lg border border-ink-900/15 bg-transparent px-2.5 py-1.5 text-sm dark:border-white/15"
            placeholder={xConfigured ? "输入新 Token 以覆盖当前配置" : "粘贴 X Bearer Token"}
            value={xToken}
            onChange={(e) => setXToken(e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
          <Button
            onClick={() => saveX.mutate(xToken)}
            loading={saveX.isPending}
            disabled={!xToken.trim()}
          >
            保存 Token
          </Button>
        </div>
        <a
          href="https://developer.x.com/"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-xs text-brand-600 hover:underline dark:text-brand-400"
        >
          如何获取？前往 X Developer Portal
          <ExternalLink className="h-3 w-3" aria-hidden />
        </a>
      </Card>

      <Card className="space-y-2 p-5 text-sm">
        <SectionTitle icon={Database} title="数据位置（只读）" />
        <div>数据库 / 数据目录：{data.data_dir_display}</div>
        <div>浏览器 Profile：{data.browser_profiles_dir_display}</div>
        <div>监听地址：{data.host}（仅本机）</div>
      </Card>

      <Card className="p-5">
        <SectionTitle
          icon={Bell}
          title="桌面通知"
          description="同步完成、失败或被取消时在系统托盘弹出通知（需要浏览器授权）。"
        />
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            <Switch
              checked={notifyEnabled}
              onChange={(enabled) => {
                setNotifyEnabledState(enabled);
                setNotifyEnabled(enabled);
                if (enabled) {
                  void requestNotificationPermission().then((granted) => {
                    if (!granted) {
                      setNotifyEnabledState(false);
                      setNotifyEnabled(false);
                      setMsg("浏览器拒绝了通知权限，请检查浏览器站点设置");
                    }
                  });
                }
              }}
              label="同步完成时通知我"
            />
            同步完成时通知我
          </label>
          <Button
            size="sm"
            variant="ghost"
            disabled={!notifyEnabled || !notificationsSupported()}
            onClick={() => {
              void requestNotificationPermission().then((granted) => {
                setMsg(granted ? "通知权限已开启" : "通知权限被拒绝，请在浏览器设置中允许本站点通知");
              });
            }}
          >
            测试通知权限
          </Button>
        </div>
        {notificationsSupported() && Notification.permission === "denied" && (
          <p className="mt-2 text-xs text-amber-600 dark:text-amber-400">
            当前浏览器已拒绝通知权限：请点击地址栏左侧的站点权限图标，将「通知」改为允许。
          </p>
        )}
      </Card>

      <Card className="p-5">
        <SectionTitle
          icon={Upload}
          title="数据备份"
          description={
            "导出 SQLite 数据库为 ZIP 文件，用于本地备份。建议定期备份以避免数据丢失。"
          }
        />
        <Button
          size="sm"
          variant="secondary"
          loading={exportMut.isPending}
          onClick={() => {
            if (confirm("确定要导出数据库备份吗？")) {
              exportMut.mutate();
            }
          }}
        >
          <Upload className="h-3.5 w-3.5" aria-hidden />
          导出备份
        </Button>
      </Card>

      <Card className="p-5">
        <SectionTitle
          icon={Trash2}
          title="数据清理"
          description={`删除超过「数据保留天数」（当前 ${data.data_retention_days} 天）的旧内容、评论与同步记录。状态为「新」或「待处理」的评论不会被删除。清理后无法恢复，建议先导出备份。`}
        />
        <Button
          size="sm"
          variant="secondary"
          loading={cleanupMut.isPending}
          onClick={() => {
            if (
              confirm(
                `将永久删除早于 ${data.data_retention_days} 天的数据（未处理的评论会保留）。此操作不可恢复，确认继续？`,
              )
            ) {
              cleanupMut.mutate();
            }
          }}
        >
          <Trash2 className="h-3.5 w-3.5" aria-hidden />
          立即清理旧数据
        </Button>
      </Card>

      <Card className="p-5">
        <SectionTitle icon={Layers} title="平台能力矩阵摘要" />
        <div className="space-y-2 text-xs">
          {platforms.data?.map((p) => (
            <div key={p.platform} className="rounded border border-ink-900/10 p-2 dark:border-white/10">
              <div className="flex items-center gap-2 font-medium">
                {p.label}
                {p.experimental && <Badge tone="warn">实验性</Badge>}
                <Badge>{p.stability}</Badge>
              </div>
              <div className="mt-1 text-ink-500">{p.notes}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function SectionTitle({
  icon: Icon,
  title,
  description,
}: {
  icon: LucideIcon;
  title: string;
  description?: string;
}) {
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-ink-900/5 text-ink-600 dark:bg-white/10 dark:text-[#c6cac2]">
        <Icon className="h-4 w-4" aria-hidden />
      </span>
      <div className="min-w-0">
        <div className="font-medium">{title}</div>
        {description && <div className="text-xs text-ink-500 dark:text-[#9aa19b]">{description}</div>}
      </div>
    </div>
  );
}
