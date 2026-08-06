# CreatorPulse

> 给多平台创作者的本地优先运营状态中心。

CreatorPulse 把账号健康、内容表现、指标趋势和评论待办放进一个清晰的工作台。它运行在你的电脑上，凭据留在本机，发布和回复仍由你自己掌控。

![CreatorPulse 总览](docs/assets/dashboard.png)

## 主要能力

- **统一总览**：账号、内容、评论、同步记录使用一致的视觉语言。
- **实时同步状态**：展示排队、登录检查、内容抓取、指标更新、评论抓取等阶段。
- **诚实的指标**：平台没有提供的字段显示为不可用，不会用 0 误导判断。
- **评论收件箱**：筛选本地处理状态，支持批量标记，再跳转原平台回复。
- **演示模式**：无需连接账号即可体验完整界面。

## 快速开始

1. 安装 Python 3.12+、Node.js 18+。
2. 双击项目根目录的 `启动 CreatorPulse.bat`。
3. 打开「设置 → 全局 Mock」，或在「账号」页添加演示账号。

停止服务请双击 `停止 CreatorPulse.bat`。开发命令、平台连接方式和架构说明见 [英文 README](README.md)。

## 安全边界

- 后端默认只监听 `127.0.0.1`。
- SQLite 数据在 `data/`，浏览器登录态在 `browser-profiles/`，都不会提交到 Git。
- X Token 保存在本机 `backend/.env.x`，API 不返回 Token 原文。
- 日志和诊断会脱敏 Cookie、Authorization、Bearer、access token、refresh token、密码等字段。
- 项目不提供验证码绕过、反检测、自动发布、删除、点赞、关注、私信或自动回复。

完整能力矩阵见 [docs/platform-support.md](docs/platform-support.md)，安全报告请先读 [SECURITY.md](SECURITY.md)。
