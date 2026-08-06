import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

/** Payload of a sync_update event pushed by /api/events. */
export interface SyncEventPayload {
  type: "sync_update";
  run_id: number;
  account_id: number;
  platform: string;
  status: string; // queued | running | success | failed | cancelled
  phase: string; // queued | checking_auth | fetching_profile | fetching_posts | fetching_metrics | fetching_comments | done
  posts_fetched?: number;
  comments_fetched?: number;
  message?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  timestamp?: string;
}

/** Latest live progress per account, driven entirely by SSE events. */
export type SyncProgressMap = Record<
  number,
  Pick<SyncEventPayload, "phase" | "status" | "posts_fetched" | "comments_fetched" | "message">
>;

const TERMINAL_STATUSES = new Set(["success", "failed", "cancelled"]);

function targetKeys(event: SyncEventPayload): string[] {
  // Any sync event can change account status, dashboard totals, and sync runs.
  // During a run, posts/comments are only touched as their counts change, so
  // refresh them too — but only when the event actually reports counts.
  const keys = ["accounts", "dashboard", "sync-runs"];
  if ((event.posts_fetched ?? 0) > 0 || (event.comments_fetched ?? 0) > 0) {
    keys.push("posts", "comments");
  }
  return keys;
}

// ---------------------------------------------------------------------------
// Module-level singleton: the whole app shares one EventSource connection so
// AppShell and AccountsPage do not each open a stream to the backend.
// ---------------------------------------------------------------------------

interface SharedState {
  progress: SyncProgressMap;
  connected: boolean;
  lastTerminal: SyncEventPayload | null;
}

const shared: SharedState = { progress: {}, connected: false, lastTerminal: null };
const listeners = new Set<() => void>();
let eventSource: EventSource | null = null;
let refCount = 0;

function emit() {
  for (const fn of listeners) fn();
}

function ensureConnected() {
  if (eventSource) return;
  const es = new EventSource("/api/events");
  eventSource = es;

  es.onopen = () => {
    shared.connected = true;
    // After a reconnect, in-flight progress from the previous connection may
    // be stale; clear it and let fresh events repopulate. The terminal event
    // stays so the notification dedupe still works.
    shared.progress = {};
    emit();
  };
  es.onerror = () => {
    // EventSource retries automatically; keep the flag accurate.
    shared.connected = false;
    emit();
  };
  es.onmessage = (msg) => {
    let event: SyncEventPayload;
    try {
      event = JSON.parse(msg.data) as SyncEventPayload;
    } catch {
      return;
    }
    if (event.type !== "sync_update") return;

    const next = { ...shared.progress, [event.account_id]: event };
    shared.progress = next;

    if (TERMINAL_STATUSES.has(event.status)) {
      delete next[event.account_id];
      shared.progress = next;
      shared.lastTerminal = event;
    }
    emit();
  };
}

function disconnectIfIdle() {
  refCount -= 1;
  if (refCount <= 0 && eventSource) {
    eventSource.close();
    eventSource = null;
    shared.connected = false;
    shared.progress = {};
    shared.lastTerminal = null;
  }
}

/**
 * Subscribe to the shared SSE stream. The underlying EventSource is a
 * singleton: the first caller opens it, the last unmount closes it.
 */
export function useSyncEvents(): {
  progress: SyncProgressMap;
  connected: boolean;
  lastTerminal: SyncEventPayload | null;
} {
  const qc = useQueryClient();
  const [state, setState] = useState<SharedState>(shared);
  const qcRef = useRef(qc);
  qcRef.current = qc;
  // Track the newest event signature already invalidated per account so each
  // consumer invalidates every distinct event exactly once.
  const seenRef = useRef<Record<number, string>>({});
  const seenTerminalRef = useRef<string>("");

  useEffect(() => {
    refCount += 1;
    const onSharedChange = () => {
      setState({ ...shared });
      // Invalidate through this consumer's own query client.
      for (const [accountIdStr, evt] of Object.entries(shared.progress) as [
        string,
        SyncEventPayload,
      ][]) {
        const accountId = Number(accountIdStr);
        const sig = `${evt.run_id}:${evt.status}:${evt.phase}:${evt.posts_fetched ?? 0}:${evt.comments_fetched ?? 0}`;
        if (seenRef.current[accountId] === sig) continue;
        seenRef.current[accountId] = sig;
        for (const key of targetKeys(evt)) {
          qcRef.current.invalidateQueries({ queryKey: [key] });
        }
      }
      // Terminal events are removed from `progress`; invalidate them too.
      const terminal = shared.lastTerminal;
      if (terminal) {
        const sig = `${terminal.run_id}:${terminal.status}`;
        if (seenTerminalRef.current !== sig) {
          seenTerminalRef.current = sig;
          for (const key of targetKeys(terminal)) {
            qcRef.current.invalidateQueries({ queryKey: [key] });
          }
        }
      }
    };
    listeners.add(onSharedChange);
    ensureConnected();
    return () => {
      listeners.delete(onSharedChange);
      disconnectIfIdle();
    };
  }, []);

  return {
    progress: state.progress,
    connected: state.connected,
    lastTerminal: state.lastTerminal,
  };
}
