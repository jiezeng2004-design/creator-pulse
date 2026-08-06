# 平台支持矩阵

状态说明：

| 状态 | 含义 |
|------|------|
| Stable | v1 可用且错误可预期 |
| Experimental | 能跑通部分路径，页面变化可能导致空结果 |
| Unsupported | 当前不做或平台不提供 |
| Requires additional permission | 需要更高 API 权限/套餐 |
| Not yet implemented | 接口预留，逻辑未完成 |

## 总表

| 平台 | 登录方式 | 帖子列表 | 浏览/曝光 | 点赞 | 收藏 | 转发 | 评论列表 | 官方已回复状态 | 本地处理状态 | 稳定性 |
|------|----------|----------|-----------|------|------|------|----------|----------------|--------------|--------|
| X | 官方 API Bearer Token | Stable | 浏览 Unsupported；曝光 Requires additional permission | Stable (`like_count`) | Unsupported | Stable (`retweet_count` 作为转发) | Requires additional permission（recent search / conversation） | Not yet implemented | Stable | Stable（有 Token 时） |
| 知乎 | Playwright 手动登录 + 本地 Profile | Experimental（创作中心 JSON/DOM） | Experimental（有则填，无则 null） | Experimental | Experimental | Unsupported / 部分 | Experimental | Not yet implemented | Stable | Experimental → 优先真实闭环 |
| 今日头条 | Playwright 手动登录 + 本地 Profile | Experimental | Experimental | Experimental | Experimental | Experimental | Experimental | Not yet implemented | Stable | Experimental |
| 小红书 | Playwright 手动登录 + 本地 Profile | Experimental（创作中心 API 拦截） | Experimental | Experimental | Experimental | Experimental | Experimental | Not yet implemented | Stable | Experimental |

## 限制条件

### X

- 推荐在 **设置 → X API 配置** 网页端填写 X Developer Portal 的 **Bearer Token**（app-only），
  保存到 `backend/.env.x`；也可手动写 `backend/.env` 的 `X_BEARER_TOKEN`（勿提交真实 Token）
- **添加 X 账号时必须填写 X 用户名**（不含 @）：app-only Bearer Token 无法调用
  `/users/me`，适配器会先按用户名解析账号（`/users/by/username`），再拉取该用户推文；
  若使用 user-context Token，则直接走 `/users/me`
- 实现：`adapters/x/` 分层为 `client.py`（tweepy `AsyncClient` 封装，MIT）、
  `errors.py`（tweepy 错误 → CreatorPulse 错误分类）、`mapper.py`（响应 → DTO）、
  `adapter.py`（编排）。依赖 `tweepy[async]`
- Free/Basic 档位能力不同；403 会显示权限不足，不会用 0 冒充
- 限流返回 `rate_limited`，诊断中可含重置时间（来自 tweepy `TooManyRequests.reset_time`，无密钥）

### 知乎

- 官方开放平台当前以搜索/热榜为主，**不覆盖个人创作者内容运营数据**
- 使用用户自己登录后的创作中心；不自动回复、不绕过验证码
- 选择器集中在 `adapters/zhihu/selectors.py`；页面改版可能触发 `selector_changed`

### 今日头条

- 目标域：`mp.toutiao.com`
- v1 提供登录、检测与实验性读取；抓取失败返回空/错误，不伪造

### 小红书

- 创作中心风控与结构变化频繁
- 支持认证检测、内容列表抓取（API 拦截 + JS 状态提取）、评论获取、时间戳解析

## Mock / 演示数据

- 开启设置「全局 Mock」或添加账号时勾选「演示数据」
- UI 顶栏显示「演示数据」横幅
- 仅用于本地 UI 与流程验收

## 参考（未复制其代码）

- X API v2 文档：https://developer.x.com/
- 知乎创作中心（用户后台）：https://www.zhihu.com/creator
- 头条号后台：https://mp.toutiao.com/
