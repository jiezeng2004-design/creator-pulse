# Contributing to CreatorPulse

Thanks for helping make creator operations calmer and safer.

## Before you start

- Read the [platform support matrix](docs/platform-support.md).
- Keep adapter behavior read-only. Do not add publishing, deletion, liking, following, private messaging, or automatic reply actions.
- Never commit `backend/.env`, `backend/.env.x`, `data/`, `browser-profiles/`, screenshots of real accounts, or raw platform responses.
- Use demo data or redacted fixtures in tests.

## Local development

Requirements: Python 3.12+, Node.js 18+, `uv`, and `pnpm`.

```powershell
.\scripts\setup.ps1
.\scripts\dev.ps1
```

The app runs on `http://127.0.0.1:5174`, with the API on `http://127.0.0.1:8001`.

## Checks

Run the full local suite before opening a pull request:

```powershell
.\scripts\test.ps1
```

Focused checks are also available:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app tests
cd ..\frontend
pnpm lint
pnpm test
pnpm build
```

## Pull requests

Describe the user problem, the behavior that changed, and the checks you ran. For platform adapters, note the platform, entry point, fields observed, and what remains experimental. Keep pull requests focused and include a screenshot for meaningful UI changes using demo data only.
