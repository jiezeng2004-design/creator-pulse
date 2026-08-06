# CreatorPulse 架构说明

## 概览

CreatorPulse 是本地优先的 Web 应用：

- **前端**：React + TypeScript + Vite，仅访问本机 API
- **后端**：FastAPI + SQLAlchemy + SQLite
- **适配器**：按平台隔离，统一 DTO；同步服务写库
- **浏览器**：国内平台使用 Playwright persistent context，Profile 存于 `browser-profiles/`

```text
UI -> /api/* -> BackgroundSync -> SyncService -> PlatformAdapter -> Platform
                    |               |                 |
                    v               v                 v
              durable queue       SQLite          (httpx / Playwright)
               (SyncRun)
```

## 模块边界

| 模块 | 职责 | 禁止 |
|------|------|------|
| `adapters/*` | 登录检测、拉帖子/指标/评论，返回标准化对象 | 写 DB、改 UI、上传凭据 |
| `sync/background.py` | 持久化排队记录、后台任务生命周期、全局并发和启动恢复 | 复用请求 session、解析平台数据 |
| `sync/service.py` | 编排同步、锁、异常分类、写 SyncRun | 直接解析 DOM |
| `services/*` | 业务 CRUD、聚合 | 调平台页面 |
| `api/*` | HTTP 契约、分页 | 业务规则堆叠 |
| `core/*` | 配置、日志脱敏、路径沙箱 | 平台逻辑 |

## 并发与限流

- `AsyncSession` 不是并发安全的。API 先持久化 `SyncRun(status=queued)`，再由
  `sync/background.py` 为每个账号打开独立 session；请求返回后不保留 request session。
- 后台执行器用信号量把全局并发限制为 3，因为每个浏览器抓取都可能启动一个
  Chromium。单账号另有独立锁，重复提交返回 409。
- 后台执行器位于当前应用进程内，队列状态则持久化在 SQLite。异常退出后不会自动
  重跑抓取；下次启动会把遗留的 `queued` / `running` 记录标记为
  `failed (error_code=interrupted)`，避免任务永久显示为进行中。
- 限流由 `core/ratelimit.py` 自实现（固定窗口，按客户端地址计数）。不使用
  slowapi：它依赖 `route.endpoint` 判断是否豁免，而 Starlette >= 1.3 会把
  `include_router` 的结果包装成没有该属性的 `_IncludedRouter`，导致所有路由
  被静默豁免。
- 定时同步以数据库中的设置为准，`.env` 只提供初始默认值，UI 关闭后必须生效；
  启用后也通过同一个后台队列执行，与手动同步共享并发上限、账号互斥和取消机制。
- Dashboard 有 60 秒 TTL 缓存，同步结束后会主动失效，避免展示同步前的旧数字。

## 同步流程

1. API 写入 `SyncRun(status=queued)` 并把账号标记为 `syncing`
2. API 立即返回任务 ID；前端通过 `/api/events` 的 SSE 实时接收进度，另有 30 秒兜底轮询
3. 后台任务获取全局并发槽和账号锁，把 SyncRun 改为 `running`
4. `check_authentication`
5. `fetch_account_profile` 更新本地账号元数据
6. `fetch_posts` → upsert
7. `fetch_post_metrics` → 更新 + MetricSnapshot
8. 逐帖 `fetch_comments` → upsert（保留 local_status）
9. 写终态 SyncRun；单账号失败不影响其他账号

### 取消同步

`POST /api/accounts/{id}/cancel` 对仍在等待并发槽的任务直接取消；任务已经开始抓取时
只设置一个标志，在下一个检查点自行退出，以便适配器正常关闭 Chromium 窗口，而不是被强杀。

- 空闲账号上调用是 no-op（返回 `cancelling: false`）。若设置标志，会残留到该账号
  的**下一次**同步并导致误取消。
- `cleanup_sync_state` 不会移除仍被持有的锁：否则并发调用者会新建一把未加锁的锁，
  从而绕过「同账号禁止并发」。
- 账号存在排队或运行任务时禁止删除，调用方需先取消并等待任务进入终态。

## 数据保留

`services/retention_service.py` 实现 `DATA_RETENTION_DAYS`（此前只是文档承诺，
从未有清理逻辑，数据库无限增长）。

- 每天执行一次，独立于定时同步开关：清理是本地维护，不访问平台。
  也可在设置页手动触发 `POST /api/settings/cleanup`。
- 帖子按 `published_at` 计龄，缺失时回退 `created_at`；两者都没有则保留不猜测。
- `new` / `pending` 的评论永不自动删除；仍持有未处理评论的过期帖子也一并保留。
- 删除帖子会级联其评论与指标快照，趋势数据不会比帖子活得更久。

## 安全

- 后端默认 `127.0.0.1`
- Profile / DB 在 `.gitignore`
- 日志与诊断 JSON 过滤 Cookie、Authorization、Token 等
- 路径必须在 `data/` 或 `browser-profiles/` 下

## 扩展新平台

1. 在 `adapters/<name>/` 实现 `PlatformAdapter`
2. 在 `registry.py` 注册
3. 补充 Mock 场景与 `docs/platform-support.md`
4. UI 会通过 `/api/platforms` 自动展示能力说明
