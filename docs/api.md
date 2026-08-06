# CreatorPulse API 参考

本文档基于 `backend/app/api/` 与 `backend/app/schemas/` 的实际实现整理。运行中的服务还提供交互式文档：`http://127.0.0.1:8001/docs`。

## 通用约定

- 基地址：`http://127.0.0.1:8001`，仅监听本机（可通过设置中的 `host` 查看）。
- 允许的前端来源：`127.0.0.1:5174` / `localhost:5174`（dev）与 `:4173`（preview）。
- 限流：固定窗口，默认每客户端 100 次 / 60 秒；`/docs`、`/redoc`、`/openapi.json`、`/api/events` 豁免。
  - 正常响应带 `X-RateLimit-Limit`、`X-RateLimit-Remaining`。
  - 超限返回 `429`，带 `Retry-After`，响应体为 `{"detail": "请求过于频繁，请稍后再试。"}`。
- 业务错误响应体为 `{"detail": {"code": ..., "message": ...}}`，映射关系：

| code | HTTP |
|------|------|
| `not_found` | 404 |
| `conflict` | 409 |
| `validation_error` | 422 |
| 其他 `AppError` | 400 |

- 分页响应统一为 `{page, page_size, total, items}`；`page >= 1`，`page_size` 取值 1–100（默认 20）。

## 健康检查

### `GET /api/health`

返回服务存活状态，用于启动脚本与前端探活。

## 平台能力

### `GET /api/platforms`

返回各平台的能力矩阵（`PlatformCapability` 列表）：登录方式、可采集的指标（posts/views/likes/favorites/shares/comments）、稳定性与 `experimental` 标记。前端据此隐藏不支持的字段。

## 账号

### `GET /api/accounts`

返回 `AccountRead` 列表。关键字段：

- `account_status`、`authentication_type`
- `last_successful_sync_at`、`last_sync_attempt_at`、`last_sync_error`
- `browser_profile_path`：仅用于展示的相对路径，不含完整密钥目录
- `next_action`：`{action, label, description, requires_user_login}`，驱动 UI 的下一步引导

### `POST /api/accounts`

请求体 `AccountCreate`：

```json
{ "platform": "x", "display_name": "", "username": null, "use_mock": false }
```

### `GET /api/accounts/{account_id}`

单个 `AccountRead`；不存在返回 404。

### `DELETE /api/accounts/{account_id}?delete_profile=false`

解除账号绑定。`delete_profile=true` 时同时删除对应浏览器 Profile 目录（不可恢复）。响应：`{"message": ..., "delete_profile": bool}`。

账号有排队中或运行中的同步任务时返回 409；请先取消任务再删除，避免后台任务写入已删除账号。

### `POST /api/accounts/{account_id}/login`

启动登录流程（国内平台会打开 Playwright 持久化窗口，由你手动完成登录）。响应 `LoginStartResponse`：`{started, message, authentication_type, instructions}`。

### `POST /api/accounts/{account_id}/check-auth`

检测登录态。响应 `AuthCheckResponse`：`{authenticated, status, message, display_name, username}`。

### `POST /api/accounts/{account_id}/refresh`

一键刷新：请求内先检测登录态，成功后把同步加入后台队列。响应 `QuickRefreshResponse`：`{account_id, authenticated, needs_login, sync_run_id, sync_status, message, next_action}`。

### `POST /api/accounts/{account_id}/sync`

同步单个账号。服务端先持久化一条 `queued` 状态的同步记录，然后立即返回 `SyncStartResponse`：

```json
{
  "sync_run_id": 12,
  "status": "queued",
  "message": "同步已加入后台队列"
}
```

浏览器抓取使用独立数据库会话在后台执行，不占用原 HTTP 连接。同一账号已有排队或运行任务时返回 409。

### `POST /api/accounts/sync-all`

把全部空闲账号加入后台队列并立即返回。已在排队或运行的账号会被跳过。响应 `SyncAllResponse`：

```json
{
  "total": 3,
  "started": 2,
  "skipped": 1,
  "items": [{ "account_id": 1, "platform": "x", "status": "queued", "message": "同步已加入后台队列", "sync_run_id": 12 }]
}
```

### `POST /api/accounts/{account_id}/cancel`

排队中的任务会直接取消；已经开始抓取的任务会在下一个检查点停止。运行中采用协作式取消：浏览器抓取只在步骤之间中断，让适配器干净地关掉 Chromium，而不是强杀进程。

响应 `SyncCancelResponse`：

```json
{ "account_id": 1, "cancelling": true, "message": "..." }
```

- 账号 id 不存在 → 404。
- 账号当前没有同步在跑时，`cancelling` 为 `false`，且不会把取消标记残留到下一次同步。

## 内容

### `GET /api/posts`

查询参数：

| 参数 | 说明 |
|------|------|
| `page` / `page_size` | 分页，默认 1 / 20（上限 100） |
| `platform` | 平台过滤 |
| `account_id` | 账号过滤 |
| `search` | 标题/摘要关键字，最长 200 字符 |
| `sort_by` | `published_at`（默认）、`view_count`、`impression_count`、`like_count`、`comment_count` |
| `sort_dir` | `desc`（默认）、`asc` |

返回 `Page[PostRead]`，`PostRead` 含 `view_count`、`impression_count`、`like_count`、`favorite_count`、`share_count`、`repost_count`、`comment_count` 与 `metrics_updated_at`；平台不支持的指标为 `null`。

### `GET /api/posts/{post_id}`

单条 `PostRead`；不存在返回 404。

### `GET /api/posts/{post_id}/metrics`

返回该帖子的历史指标快照 `MetricSnapshotRead` 列表：`{id, post_id, captured_at, view_count, ...}`。内容列表中的趋势面板会在展开时按需调用此接口。

## 评论

### `GET /api/comments`

查询参数：`page`、`page_size`、`local_status`、`platform`、`account_id`、`post_id`、`search`（≤200 字符）。

返回 `Page[CommentRead]`，附带 `post_title`、`post_url`、`account_display_name` 便于直接跳转平台处理。

### `PATCH /api/comments/{comment_id}/status`

更新本地处理状态（仅本地标记，不会代替你在平台回复）。请求体：

```json
{ "local_status": "handled" }
```

响应更新后的 `CommentRead`；不存在返回 404。

## 仪表盘

### `GET /api/dashboard/summary`

返回 `DashboardSummary`：24h/7d 发帖数、总浏览量、总互动、新评论与待处理评论数、`platforms` 平台卡片列表、`mock_mode`、`last_global_sync_at`。

结果带 60 秒 TTL 缓存；同步完成后缓存会被主动失效，所以同步后立刻刷新就能看到新数据。

## 同步记录

### `GET /api/sync-runs`

查询参数：`page`、`page_size`、`account_id`、`platform`。按 `started_at` 倒序。

返回 `Page[SyncRunRead]`：`{id, account_id, platform, account_display_name, sync_type, status, started_at, finished_at, posts_fetched, comments_fetched, error_code, error_message, diagnostic}`。`status` 可能为 `queued`、`running`、`success`、`partial`、`failed` 或 `cancelled`；`diagnostic` 是脱敏后的排错信息。

## 设置

### `GET /api/settings`

返回 `SettingsRead`：`enable_scheduled_sync`、`sync_interval_minutes`、`sync_max_posts`、`data_retention_days`、`dev_mode`、`enable_mock_data`、`data_dir_display`、`browser_profiles_dir_display`、`host`、`updated_at`。

### `PATCH /api/settings`

部分更新，字段均可选并有约束：

| 字段 | 约束 |
|------|------|
| `enable_scheduled_sync` | bool；关闭后定时同步真正停止 |
| `sync_interval_minutes` | ≥ 30 |
| `sync_max_posts` | 1–200 |
| `data_retention_days` | 7–3650 |
| `dev_mode` / `enable_mock_data` | bool |

修改调度相关字段会重启调度器。响应为更新后的 `SettingsRead`。

### `POST /api/settings/cleanup`

立即按保留策略清理，无需等待每日任务。删除早于 `cutoff` 的帖子、评论、指标快照与同步记录；`new` / `pending` 状态的评论及其所属帖子始终保留。

响应 `CleanupResponse`：

```json
{
  "retention_days": 365,
  "cutoff": "2025-08-03T11:45:00+00:00",
  "posts_deleted": 12,
  "comments_deleted": 30,
  "snapshots_deleted": 48,
  "sync_runs_deleted": 7,
  "total_deleted": 97,
  "message": "..."
}
```

### `POST /api/settings/export`

导出 SQLite 数据库为 ZIP（含 `.env.example` 作为参考，不含真实 `.env`）。响应为 `application/zip` 流，文件名形如 `creator_pulse_backup_20260803_194500.zip`。

- 数据库文件不存在 → 404。
- 数据库路径超出项目沙箱 → 403。
- 导出使用 SQLite 备份 API 生成一致性快照：即使数据库运行在 WAL 模式下，尚未 checkpoint 的已提交数据也会包含在备份中。快照与压缩在工作线程中执行，不阻塞事件循环。

### `GET /api/settings/x-credentials`

返回 `{ "configured": boolean }`，表示应用当前是否持有非空的 X Bearer Token。**不会返回 Token 本身**。

### `PUT /api/settings/x-credentials`

请求体 `{ "x_bearer_token": "..." }`，将 Token 持久化到应用自有的 `backend/.env.x`（gitignored），覆盖手动编辑的 `backend/.env` 值，并在下一次创建 X 适配器时立即生效，无需重启。响应同样只包含 `{ "configured": true }`，Token 不会回显。

## 实时事件流

### `GET /api/events`（SSE）

Server-Sent Events 长连接，推送同步进度。前端用 `EventSource` 订阅；服务端 15 秒心跳保活，断线由浏览器按 `retry: 2000` 自动重连。本端点豁免限流。

事件格式（`data:` 行为 JSON）：

```json
{
  "type": "sync_update",
  "run_id": 12,
  "account_id": 3,
  "platform": "zhihu",
  "status": "running",
  "phase": "fetching_posts",
  "posts_fetched": 5,
  "comments_fetched": 2,
  "message": null,
  "timestamp": "2026-08-04T12:00:00+00:00"
}
```

- `status`：`queued` / `running` / `success` / `failed` / `cancelled`
- `phase`：`queued` / `checking_auth` / `fetching_profile` / `fetching_posts` / `fetching_metrics` / `fetching_comments` / `done`
- `posts_fetched` / `comments_fetched` 为实时累计值（仅 `fetching_posts` / `fetching_comments` 阶段更新）
- 终态事件额外携带 `error_code` / `error_message`（失败/取消时）

## 评论

### `POST /api/comments/batch-status`

批量设置评论本地状态，一次请求最多 500 条：

```json
{ "comment_ids": [1, 2, 3], "local_status": "handled" }
```

- `local_status` 取值：`new` / `pending` / `handled` / `ignored`
- 不存在的 id 静默跳过（不报错）
- 响应：`{ "updated": 3, "status": "handled" }`

### 同步记录扩展字段

`GET /api/sync-runs` 的每一项新增 `phase` 字段（与上述事件阶段一致），页面刷新后可恢复运行中记录的进度展示。
