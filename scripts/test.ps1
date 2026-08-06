# CreatorPulse test / lint / build
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$failed = $false

Write-Host "== Backend tests ==" -ForegroundColor Cyan
Set-Location "$Root\backend"
& .\.venv\Scripts\python.exe -m pytest -q
if ($LASTEXITCODE -ne 0) { $failed = $true }

Write-Host "== Ruff ==" -ForegroundColor Cyan
& .\.venv\Scripts\python.exe -m ruff check app tests
if ($LASTEXITCODE -ne 0) { $failed = $true }

Write-Host "== Pyright ==" -ForegroundColor Cyan
& .\.venv\Scripts\python.exe -m pyright app tests
if ($LASTEXITCODE -ne 0) {
    Write-Host "Pyright 有告警（非阻塞记录）" -ForegroundColor Yellow
}

Write-Host "== Frontend lint ==" -ForegroundColor Cyan
Set-Location "$Root\frontend"
pnpm lint
if ($LASTEXITCODE -ne 0) { $failed = $true }

Write-Host "== Frontend tests ==" -ForegroundColor Cyan
pnpm test
if ($LASTEXITCODE -ne 0) { $failed = $true }

Write-Host "== Frontend build ==" -ForegroundColor Cyan
pnpm build
if ($LASTEXITCODE -ne 0) { $failed = $true }

Set-Location $Root
if ($failed) {
    Write-Host "部分检查失败" -ForegroundColor Red
    exit 1
}
Write-Host "全部通过" -ForegroundColor Green
