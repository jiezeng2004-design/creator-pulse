# CreatorPulse 适配器设计

> 依据《参考仓库审计》（`reference-audit.md`）形成的适配器分层与实现方案。
> 核心原则：第三方数据必须经过转换层进入 CreatorPulse 的 DTO，禁止第三方模型
> 直接渗透进数据库与前端；CreatorPulse 保留自己的统一 `PlatformAdapter` 接口。

## 1. 分层结构

```text
backend/app/adapters/
├─ base.py            # PlatformAdapter 抽象（CreatorPulse 唯一接口）
├─ registry.py        # 工厂 + 平台能力声明
├─ types.py           # 标准化 DTO（PlatformPost/PlatformComment/Metrics/Profile）
├─ exceptions.py      # 统一错误分类
├─ browser.py         # Playwright 持久化上下文（国内平台共用）
├─ x/
│  ├─ adapter.py      # XAdapter（编排）
│  ├─ client.py       # tweepy AsyncClient 封装（计划）
│  ├─ mapper.py       # X 响应 -> PlatformPost/Comment（计划）
│  └─ errors.py       # tweepy 错误 -> AdapterError（计划）
├─ xiaohongshu/
├─ zhihu/
├─ toutiao/
└─ mock/
```

约束：

- 适配器不写数据库、不发起任何平台写操作（无发布/回复/点赞/收藏/删除方法）
- 所有外部响应先经字段提取/类型校验再进入 DTO
- 一个适配器失败不导致整个同步任务崩溃（sync/service.py 已按账号隔离）

## 2. X 接入方案（tweepy 正式依赖）

### 认证

- **app-only Bearer Token**（X Developer Portal 默认）：可调用 `/users/by/username`、
  `/users/{id}/tweets`、`/tweets`、`/tweets/search/recent`；**不能**调用 `/users/me`
- **user-context token**：可调用 `/users/me`

### 流程（当前已实现，`adapters/x/adapter.py`）

1. `check_authentication` → 优先 `_fetch_me()`（user-context），401/403 回退
   `_resolve_user()`（app-only：按账号 username 查 `/users/by/username`）
2. `fetch_posts` → 用解析出的 `user.id` 调 `/users/{id}/tweets`
3. `fetch_post_metrics` → 批量 `/tweets?ids=...&tweet.fields=public_metrics`
4. `fetch_comments` → `/tweets/search/recent?query=conversation_id:...`（需更高权限时
   明确返回 unsupported，不伪造）

### 迁移到 tweepy 的收益与边界

- 收益：官方限流/错误语义（`TooManyRequests.retry_after`、`Forbidden`）、分页
  `AsyncPaginator`、字段展开
- 边界：CreatorPulse 仍自己实现 Token 配置（网页端 `.env.x`）、权限检测、
  限流状态持久化、数据标准化与 UI 错误提示
- 不声称当前 Token 无权访问的指标可用（impression 等保持 null + 明确标注）

### 错误分类映射（计划）

| tweepy 异常 | CreatorPulse AdapterError | 账号状态 |
| ----------- | ------------------------- | -------- |
| Unauthorized (401) | AuthenticationRequiredError | login_required |
| Forbidden (403) | PermissionDeniedError / UnsupportedFeatureError | error |
| TooManyRequests (429) | RateLimitError（含 retry_after） | rate_limited |
| NetworkError / Timeout | NetworkError / PlatformTemporaryError | error |
| BadRequest (400) | PlatformTemporaryError（含诊断） | error |

## 3. 小红书方案对比

### 方案 A：本地 Sidecar（xiaohongshu-mcp）

优点：社区维护的只读+登录能力成熟、可快速接入。
缺点：

- Go 二进制 + 内置 headless_browser（指纹/stealth/代理）——违反 CreatorPulse 风控约束
- 内含发布/评论/点赞等写工具，必须由 CreatorPulse 层白名单
- 增加部署复杂度（需单独拉取/构建二进制）

### 方案 B：原生 Playwright Adapter（推荐）

CreatorPulse 已有 `browser.py`（持久化 Profile + 手动登录）与 XHS 骨架。
独立实现：

- 登录：手动登录窗口 + Cookie 持久化（与知乎/头条一致）
- 内容列表：`creator.xiaohongshu.com` 创作者后台笔记管理，滚动分页
- 笔记详情/指标：创作者后台数据接口（`/api/galaxy/...`，仅当可读时）
- 评论：当前创作平台无评论管理入口时明确返回 unsupported（现状已实现）

**结论**：默认方案 B；sidecar 仅作为“用户已自行运行且启用”时的可选集成点，
且只调用只读 handler（工具白名单在 CreatorPulse 层实现），Sidecar 不可用不影响其他平台。

### 实施状态（2026-08-05）

- [x] `adapters/xiaohongshu/sidecar_client.py`：只读白名单客户端（仅 localhost、
  超时、响应校验、写端点拒绝、健康检查），测试见 `tests/test_xhs_sidecar_client.py`
- [ ] 将 sidecar 接入 `XiaohongshuAdapter` 作为可选数据源（需真实账号 + sidecar 运行验证）

## 4. 知乎独立实现

MediaCrawler 仅用于理解公开流程，不复制源码。当前实现已独立：

- 登录：Playwright 手动登录 + Profile 持久化
- 内容：创作者后台 JSON API（`/api/v4/creators/creations/v2/all`）+ 会员接口回退
- 评论：`comment_v5` 接口（answer/article）
- 错误：`SelectorChangedError` 明确标识页面变化

后续强化：字段校验（`_as_dict` 防御已加）、页面结构变化时给出可操作诊断。

## 5. 今日头条独立实现

`toutiao_mcp_server` 因无许可证与写操作被拒绝；仅从 README 确认功能入口：

- 创作中心：`mp.toutiao.com` 登录、内容管理页、数据统计
- 指标字段：阅读/点赞/评论/分享（`go_detail_count`、`digg_count`、`comment_count` 等）

CreatorPulse 已独立实现登录检测、内容列表（API 拦截 + 分页重放）、评论读取骨架。
保持独立，不复制其选择器或配置。

## 6. 只读白名单

- 适配器层：`PlatformAdapter` 只声明只读方法，不存在写方法
- Sidecar 场景：CreatorPulse 侧维护允许调用的工具名列表（仅只读 handler），
  请求超时、响应结构校验、异常映射
- 前端隐藏按钮不作为安全边界（后端同样不提供写 API）

## 7. 实施顺序与验证

```text
Mock 闭环（已验证：Dashboard/帖子/评论/同步/账号状态/Mock 指标 null）
→ X 真实接入（tweepy；已完成 httpx 版，计划迁移 SDK）
→ 小红书原生只读（需真实账号验证）
→ 知乎强化（已有骨架，需真实账号验证）
→ 头条强化（已有骨架，需真实账号验证）
```

每完成一个阶段：跑测试 → 更新 `docs/platform-support.md` → 更新
`docs/reference-audit.md` 的“待办/未验证”清单。
