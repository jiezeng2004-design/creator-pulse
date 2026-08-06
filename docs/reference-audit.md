# CreatorPulse 参考仓库审计

> 依据任务书对 8 个开源仓库进行许可证、安全与架构审计。参考仓库仅放置在
> CreatorPulse 目录之外（`../creatorpulse-references/`），不进入本仓库版本控制。
>
> 本文件记录审计结论，作为后续选择性复用 / 独立实现 / 明确拒绝的依据。

审计日期：2026-08-05

## 1. 结论总表

| 仓库 | 当前用途 | 许可证 | 是否允许复制 | 是否允许作为依赖 | 相关模块 | 安全风险 | 最终决定 |
| -- | ---- | --- | ------ | -------- | ---- | ---- | ---- |
| tweepy/tweepy | X API v2 客户端 | MIT | 是（保留版权） | 是 | XAdapter / X client | 低（仅 SDK；无凭据） | direct_dependency |
| xpzouying/xiaohongshu-mcp | 小红书登录/笔记/评论流程参考 | Apache-2.0 | 有条件（仅只读部分，保留归属与 NOTICE） | 否（Go 二进制 sidecar 可选） | 小红书适配器 | 中（内置发布/评论/点赞写工具、指纹/代理机制） | selective_reuse_with_attribution |
| inovector/mixpost | 领域模型与 Provider 抽象参考 | MIT | 是（保留版权） | 否 | 账号/内容/指标模型 | 低 | architecture_reference_only |
| brightbeanxyz/brightbean-studio | 统一收件箱与同步架构参考 | AGPL-3.0 | 否（clean-room） | 否 | 评论收件箱 | 低 | architecture_reference_only |
| gitroomhq/postiz-app | X Provider / OAuth / 限流架构参考 | AGPL-3.0 | 否（clean-room） | 否 | XAdapter / 限流 | 低 | architecture_reference_only |
| NanmiCoder/MediaCrawler | 多平台抓取流程行为参考 | NON-COMMERCIAL LEARNING LICENSE 1.1 | 否 | 否 | 知乎/小红书流程 | 中（代理池/反检测机制，禁止引入） | behavior_reference_only |
| chemany/toutiao_mcp_server | 头条功能入口确认 | 无许可证（保留所有权利） | 否 | 否 | 头条流程 | 高（硬编码 Token、用户名密码登录、发布/删除、自动下载 WebDriver） | rejected |
| xpzouying/x-mcp | 浏览器插件产品体验参考 | 无许可证（保留所有权利） | 否 | 否 | 登录态复用 / 操作可见性 | 中（依赖远程 Token 平台 aredink.com） | behavior_reference_only |

> 说明：任务书最低建议与实测一致；`toutiao_mcp_server` 与 `x-mcp` 实测无
> LICENSE 文件（GitHub API `license: NONE`），按“保留所有权利”处理。

## 2. 仓库级审计详情

### 2.1 tweepy/tweepy —— direct_dependency

- 许可证：MIT（`LICENSE`，Copyright (c) 2009-2023 Joshua Roesslein）【已从代码确认】
- 版本/活跃度：4.17.0，2026-07-02 发布；11.1k star；104 open issues【GitHub API】
- 结构：`tweepy/client.py`（同步 `Client`）、`tweepy/asynchronous/client.py`（`AsyncClient`）、`errors.py`、`pagination.py`、`auth.py`【已从代码确认】
- 关键能力（已从代码确认）：
  - `AsyncClient.get_me(user_auth=True)` —— 用户上下文
  - `get_user(id=, username=)` —— 支持按用户名解析（app-only Bearer 可用）
  - `get_users_tweets(id)`、`get_tweets(ids)`、`search_recent_tweets(query)` —— 帖子/指标/会话回复
  - `public_metrics` 字段展开、分页 `AsyncPaginator`
  - `Forbidden`（403 权限）、`TooManyRequests`（429，含 `retry_after`）等错误类型【已从代码确认】
- 凭据扫描：仅 `cassettes/testmediauploadgif.yaml` 出现 AWS key 样式的测试 fixture，非真实凭据【已从代码确认】
- 写操作：仅测试文件；SDK 本身提供发布 API 但 CreatorPulse 不使用
- 远程服务：仅 X API 本身
- 决定：作为 `tweepy` 正式依赖接入 XAdapter（替换手写 httpx 调用），数据仍经 CreatorPulse 的 `PlatformAdapter` DTO 标准化。

### 2.2 xpzouying/xiaohongshu-mcp —— selective_reuse_with_attribution

- 许可证：Apache-2.0（`LICENSE`）【已从代码确认】
- 活跃度：15.1k star；65 open issues；2026-08-03 最近提交【GitHub API】
- 结构：Go 实现，`cmd/`（HTTP + MCP 服务）、`browser/`（headless_browser 封装）、`cookies/`、`handlers_api.go`、`mcp_handlers.go`【已从代码确认】
- 能力（已从代码确认）：
  - 登录：二维码登录、`CheckLoginStatus`、Cookie 持久化
  - 只读：`ListFeeds`、`GetFeedDetail`（xsec_token 参数）、`GetMyProfile`、`UserProfile`、评论加载（一级 + 子评论分页，`ClickMoreReplies` / `MaxRepliesThreshold`）
  - 写操作（CreatorPulse 禁止）：`PublishContent`、`PublishVideo`、`LikeFeed`、`FavoriteFeed`、`PostComment`、`ReplyComment`、`ReplyNotification`、`LikeNotification`、`DeleteCookies`
- 风险：
  - 内置浏览器带指纹 seed、代理、stealth 选项（`browser.go` 已确认）——违反 CreatorPulse“不引入隐身浏览器 / 反检测 / 代理”约束
  - 写操作接口存在，若作 sidecar 必须在 CreatorPulse 层白名单拦截（只调用只读 handler）
- 决定：sidecar 方案评估后**不采纳为默认**（依赖 Go 二进制 + 内部风控机制）；仅研究其
  登录 Cookie 持久化、笔记列表/详情、xsec_token 流转、评论分页的**行为与字段**，用
  CreatorPulse 现有 Playwright 方案独立实现。若未来选择复用，只允许复制 Apache-2.0
  许可的只读解析逻辑并保留 LICENSE / NOTICE / 修改说明。

### 2.3 inovector/mixpost —— architecture_reference_only

- 许可证：MIT（`LICENSE.md`，Copyright (c) 2022-present, Dima Botezatu, Inovector）【已从代码确认】
- 活跃度：3.5k star；33 open issues；2026-03-16 最近提交【GitHub API】
- 领域模型（已从代码确认）：`Account`、`Post`、`PostVersion`、`Metric`、`ImportedPost`、
  `Service`（Provider 注册/能力）、`SocialProviders/{Twitter,Meta,Mastodon}`、`Setting`
- 与 CreatorPulse 的对应关系：
  - `Account` ≈ `PlatformAccount`
  - `Post` + `Metric` ≈ `Post` + `MetricSnapshot`
  - `Service` / `SocialProviders` ≈ `adapters/registry.py` + `platform_capabilities()`
  - `ImportedPost`（导入历史去重）≈ `post_service.upsert_post` 的唯一键 upsert
- 决定：仅作为领域模型与模块边界参考；CreatorPulse 已是 FastAPI+React，不引入 PHP/Laravel。

### 2.4 brightbeanxyz/brightbean-studio —— architecture_reference_only（clean-room）

- 许可证：AGPL-3.0（`LICENSE`）【已从代码确认】
- 活跃度：2.1k star；26 open issues；2026-07-12 最近提交【GitHub API】
- 架构（已从代码确认，`development_specs/architecture.md`）：Django + DRF + HTMX + Tailwind；
  `providers/base.py` 定义 `SocialProvider` 抽象，按平台实现；`inbox`（统一收件箱）、
  `social_accounts`（OAuth 连接）、`analytics`、`credentials` 模块
- 值得参考的概念：统一消息模型（评论/提及/私信）、本地处理状态、去重、增量同步、平台能力矩阵
- CreatorPulse 独立实现现状：`comments` 表已含 `platform_comment_id` 唯一键（去重）、
  `local_status`（new/pending/handled/ignored）、`first_seen_at/last_seen_at`（增量）、
  `replied_by_owner`（线程）
- 第一版不需要：多账号分配、提及/私信统一模型、审批流、白标
- 决定：不复制任何源码；仅行为与数据模型参考。

### 2.5 gitroomhq/postiz-app —— architecture_reference_only

- 许可证：AGPL-3.0（`LICENSE`）【已从代码确认】
- 活跃度：34.3k star；237 open issues；2026-08-04 最近提交【GitHub API】
- X Provider（已从代码确认，`libraries/nestjs-libraries/src/integrations/social/x.provider.ts`）：
  - 使用 `twitter-api-v2` SDK（CreatorPulse 对应选 tweepy）
  - `maxConcurrentJob = 1`（X 限流严格，CreatorPulse 的全局并发上限 3 已按账号锁约束）
  - OAuth 流程、refresh token、`handleErrors` 区分 refresh-token / bad-body / retry
  - Provider 能力声明（`SocialProvider` 接口、`identifier`/`name`）
- 决定：仅架构参考；XAdapter 用 tweepy + CreatorPulse 自己的错误分类与限流状态。

### 2.6 NanmiCoder/MediaCrawler —— behavior_reference_only

- 许可证：NON-COMMERCIAL LEARNING LICENSE 1.1（`LICENSE`，明确禁止商业使用）【已从代码确认】
- 活跃度：59.9k star；185 open issues；2026-08-04 最近提交【GitHub API】
- 结构（已从代码确认）：`base/`（平台抽象）、`media_platform/`、`proxy/`、`cache/`、
  `database/`、`webui/`、`docs/`
- 风险：`proxy/`（代理池 + IP 轮换）、Redis/Mongo 密码配置——违反 CreatorPulse 约束
- 决定：禁止复制任何源码；仅用于理解知乎登录/内容/评论分页的公开流程行为。

### 2.7 chemany/toutiao_mcp_server —— rejected

- 许可证：无 LICENSE 文件【已从代码确认 + GitHub API `license: NONE`】
- 活跃度：64 star；2 open issues；2025-06-06 最近提交【GitHub API】
- 风险（已从代码确认）：
- 硬编码凭据：`integration_example.py` 中出现疑似真实 Token（本文不保留原始值）
  - `auth.py` / `server.py` 提供 `login_with_credentials(username, password)` 用户名密码自动登录
  - 发布/删除/多平台一键发布：`publish_article`、`publish_micro`、`delete_article`、`upload`、`MultiPlatformPublisher`
  - `webdriver-manager` 自动下载 WebDriver
  - 顶层包含 `publish_test_final.log`、`complete_upload_test.log` 等测试日志（可能含环境信息）
- 决定：**拒绝**。不复制任何代码/选择器/配置，仅从 README 确认头条创作中心功能入口
  （`mp.toutiao.com` 登录、内容列表、指标字段、分析模块）。

### 2.8 xpzouying/x-mcp —— behavior_reference_only

- 许可证：无 LICENSE 文件【已从代码确认 + GitHub API `license: NONE`】
- 依赖：需要注册 aredink.com 并获取远程 API Token 绑定插件【README 已确认】
- 参考价值（产品体验，非代码）：操作完全可见、复用用户日常浏览器登录态、连接状态展示、用户主动授权
- 决定：不接入（依赖远程服务且无许可证）；CreatorPulse 已通过本地 Playwright 持久化
  Profile + 手动登录窗口实现等效体验。

## 3. CreatorPulse 最终适配器设计要点

详见 [`docs/adapter-design.md`](./adapter-design.md)。摘要：

- 保留 `PlatformAdapter` 统一接口，第三方数据一律经 DTO 转换层进入数据库
- X：`tweepy.AsyncClient` 作正式依赖；app-only Bearer + 用户名解析；user-context 回退
- 小红书：原生 Playwright 独立实现（不从 xiaohongshu-mcp 复制风控机制）；sidecar 列为可选
  集成点但默认不启用
- 知乎/头条：保持独立实现，强化错误分类与页面变化识别
- 只读白名单：适配器层不暴露任何写方法；sidecar 场景在 CreatorPulse 层做工具白名单

## 4. 安全风险清单

| # | 风险 | 来源 | 处置 |
| -- | ---- | ---- | ---- |
| 1 | 硬编码 APP_TOKEN | toutiao_mcp_server | 不引入；扫描确保 CreatorPulse 无此问题 |
| 2 | 用户名密码自动登录 | toutiao_mcp_server | 不引入；CreatorPulse 仅手动登录 |
| 3 | 发布/删除/回复写工具 | xiaohongshu-mcp、toutiao_mcp_server | CreatorPulse 适配器无写方法；sidecar 白名单 |
| 4 | 指纹/stealth/代理 | xiaohongshu-mcp、MediaCrawler | 不引入 |
| 5 | 远程 Token 平台依赖 | x-mcp | 不接入 |
| 6 | 自动下载 WebDriver/浏览器二进制 | toutiao_mcp_server、xiaohongshu-mcp(browser_download.go) | 不引入 |
| 7 | 代理池/IP 轮换 | MediaCrawler | 不引入 |
| 8 | 测试日志/数据库文件 | toutiao_mcp_server（*.log） | 不复制；参考目录不入库 |

## 5. 第一阶段任务清单（已/待办）

- [x] 浅克隆 8 仓库到 `../creatorpulse-references/`
- [x] 许可证审计（LICENSE 文件 + GitHub API 交叉确认）
- [x] 凭据/写操作/远程服务扫描
- [x] `docs/reference-audit.md`
- [x] `THIRD_PARTY_NOTICES.md`
- [x] `docs/adapter-design.md`
- [x] 实施：Mock 闭环验证（后端 96 测试全绿）→ X 真实接入（tweepy 封装 + 错误映射 + 单测）→ 平台矩阵更新
- [x] 小红书只读 Sidecar 客户端（白名单 + 超时 + 校验 + 测试）
- [ ] 需真实 Token 验证：X 各档位实际可获取指标集合
- [ ] 需真实账号验证：小红书/知乎/头条抓取字段完整性

## 6. 已确认 / 仅声称 / 未验证 区分

- **已从代码确认**：各仓库许可证文件、目录结构、X 工具清单、写操作、凭据扫描结果、
  tweepy AsyncClient API、postiz XProvider 结构、mixpost 领域模型
- **仅从 README 声称**：xiaohongshu-mcp 登录二维码与笔记详情字段、x-mcp 插件“零配置”
- **需要真实账号才能验证**：小红书/知乎/头条登录后抓取字段完整性、评论分页是否与
  当前页面结构一致、X 各 Token 档位可获取的指标集合
