import { useEffect, useRef } from "react";

/**
 * Browser desktop notifications for sync completion.
 *
 * Opt-in: the user grants permission via the browser prompt, and the feature
 * can be toggled in Settings (stored locally). Notifications only fire for
 * terminal sync states (success / failed / cancelled), so they do not spam.
 */

const NOTIFY_KEY = "cp_sync_notifications";

export function getNotifyEnabled(): boolean {
  try {
    return localStorage.getItem(NOTIFY_KEY) === "true";
  } catch {
    return false;
  }
}

export function setNotifyEnabled(enabled: boolean): void {
  try {
    if (enabled) localStorage.setItem(NOTIFY_KEY, "true");
    else localStorage.setItem(NOTIFY_KEY, "false");
  } catch {
    /* ignore storage errors */
  }
}

export function notificationsSupported(): boolean {
  return typeof window !== "undefined" && "Notification" in window;
}

/** Ask the browser for permission; resolves to true when notifications work. */
export async function requestNotificationPermission(): Promise<boolean> {
  if (!notificationsSupported()) return false;
  if (Notification.permission === "granted") return true;
  if (Notification.permission === "denied") return false;
  try {
    return (await Notification.requestPermission()) === "granted";
  } catch {
    return false;
  }
}

export function showSyncNotification(opts: {
  title: string;
  body?: string;
}): void {
  if (!notificationsSupported() || Notification.permission !== "granted") return;
  try {
    new Notification(opts.title, {
      body: opts.body,
      tag: "creatorpulse-sync",
      icon: undefined,
    });
  } catch {
    /* notification failed — non-critical */
  }
}

export function useNotifyOnSyncEvent(
  status: string | null,
  accountLabel?: string | null,
  runId?: number | null,
): void {
  const lastNotified = useRef<string>("");
  useEffect(() => {
    if (!status || !runId || !getNotifyEnabled()) return;
    const key = `${runId}:${status}`;
    if (key === lastNotified.current) return;
    lastNotified.current = key;
    const title = status === "success"
      ? "同步完成"
      : status === "failed"
        ? "同步失败"
        : status === "cancelled"
          ? "同步已取消"
          : null;
    if (!title) return;
    showSyncNotification({
      title: `${title}${accountLabel ? `：${accountLabel}` : ""}`,
      body: status === "success" ? "账号数据已更新" : "请查看同步记录确认详情",
    });
  }, [status, accountLabel, runId]);
}
