# 开发指南

## 环境

- Windows 10/11
- Python 3.12 + uv
- Node.js 18+ + pnpm

## 初始化

```powershell
.\scripts\setup.ps1
```

## 开发启动

```powershell
.\scripts\dev.ps1
```

- API: http://127.0.0.1:8001/docs
- UI: http://127.0.0.1:5174

## 测试

```powershell
.\scripts\test.ps1
```

单独后端：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

## 选择器维护

国内平台 DOM 变化时：

1. 查看 `SyncRun` 中 `error_code=selector_changed` 与脱敏诊断
2. 更新对应 `adapters/<platform>/selectors.py`
3. 在 `pages/*.py` 调整页面对象，避免把选择器散落业务层
4. 用真实账号手动验证后更新 `docs/platform-support.md`

## 安全注意

- 不要在日志打印完整 HTML、Cookie、Token
- 不要把 `data/`、`browser-profiles/`、`.env` 提交 Git
- 前端不得要求用户粘贴任意本机绝对路径用于写操作

## 目录约定

```text
backend/app/adapters/<platform>/
  adapter.py
  selectors.py
  parser.py
  pages/
```
