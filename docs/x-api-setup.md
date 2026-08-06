# X（Twitter）API 申请与配置（简版）

CreatorPulse 通过 **官方 API** 读取你自己的推文数据，不会用浏览器登录 X。

## 1. 申请开发者账号

1. 打开：https://developer.x.com/
2. 使用你的 X 账号登录
3. 申请 Developer 访问（按页面提示填写用途，可写：personal analytics for my own posts）
4. 等待审核通过（有时即时，有时需等待）

> 注意：X 的免费/付费套餐会变化。免费档通常只能做少量读取；若权限不足，CreatorPulse 会显示「权限不足」，不会伪造数据。

## 2. 创建 Project + App

1. 在 Developer Portal 创建 **Project**
2. 在 Project 下创建 **App**
3. 打开 App 的 **Keys and tokens**

## 3. 需要复制的密钥

至少准备其一：

### 方式 A（推荐入门）：Bearer Token（App-only）

- 在 Keys and tokens 里生成 **Bearer Token**
- 写入 `backend/.env`：

```env
X_BEARER_TOKEN=粘贴你的BearerToken
```

限制：`/users/me` 等用户上下文接口可能不可用。若同步失败提示权限不足，请改用方式 B。

### 方式 B：OAuth 1.0a 用户密钥（读自己账号更稳）

在 App 中生成：

- API Key / API Key Secret（即 Client ID/Secret 在部分页面的名称不同）
- Access Token / Access Token Secret（需绑定你的用户账号）

写入：

```env
X_BEARER_TOKEN=
X_CLIENT_ID=你的_API_Key
X_CLIENT_SECRET=你的_API_Key_Secret
X_ACCESS_TOKEN=你的_Access_Token
X_ACCESS_TOKEN_SECRET=你的_Access_Token_Secret
```

> 当前 v1 适配器优先使用 `X_BEARER_TOKEN`。如需 OAuth1 支持请联系项目维护者。

## 4. 在 CreatorPulse 中连接

1. 保存 `.env` 后**重启后端**
2. 账号管理 → 添加 **X**（不要勾选演示数据）
3. 点击 **检查登录状态**
4. 成功后点 **同步**
5. 在内容列表 / 总览查看真实数据

## 5. 安全

- 不要把 Token 发给任何人
- 不要提交 `.env` 到 Git（项目已忽略）
- 泄露后立刻在 Developer Portal 重新生成并作废旧密钥
