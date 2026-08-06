# Third-Party Notices

CreatorPulse 目前**未复制**任何第三方仓库的源码、模板、选择器或大段实现。

参考仓库仅放置在 `../creatorpulse-references/`（本仓库之外），用于许可证审计、
行为研究、架构对比，不进入本仓库版本控制。

## 计划/已使用的第三方组件

| 组件 | 来源 | 许可证 | 状态 |
| ---- | ---- | ------ | ---- |
| tweepy | https://github.com/tweepy/tweepy | MIT | 已使用（`tweepy[async]>=4.17.0`，X API v2 客户端） |
| lucide-react | https://lucide.dev | ISC | 已使用（前端图标库） |
| @fontsource-variable/inter | https://fontsource.org | OFL-1.1（字体） | 已使用（自托管 Inter 可变字体，替代 Google Fonts CDN） |
| @fontsource-variable/jetbrains-mono | https://fontsource.org | OFL-1.1（字体） | 已使用（自托管 JetBrains Mono 可变字体，替代 Google Fonts CDN） |

## 若未来选择性复用 Apache-2.0 / MIT 代码

必须在本文件追加以下记录（每项一条）：

- 仓库与原始文件路径
- 原始提交 SHA
- 许可证与版权声明原文
- 复制/修改的文件清单
- 修改内容说明
- 保留的版权信息位置
- 使用原因

Apache-2.0 代码还必须保留原 LICENSE、版权声明、修改说明，以及原项目 NOTICE
（如存在）。AGPL-3.0、非商业许可证、无许可证的仓库**不得复制代码**。

## 禁止复制清单

- brightbean-studio（AGPL-3.0）：clean-room，仅架构参考
- postiz-app（AGPL-3.0）：clean-room，仅架构参考
- MediaCrawler（NON-COMMERCIAL LEARNING LICENSE 1.1）：仅行为参考
- toutiao_mcp_server（无许可证）：拒绝，不复制任何内容
- x-mcp（无许可证）：仅产品体验参考
- xiaohongshu-mcp（Apache-2.0）：仅研究其只读行为；风控机制（指纹/代理/stealth）不引入
