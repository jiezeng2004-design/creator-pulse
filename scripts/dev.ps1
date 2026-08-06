# Start CreatorPulse backend + frontend (Windows)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$backendPy = Join-Path $Root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $backendPy)) {
    throw "未找到后端虚拟环境，请先运行 .\scripts\setup.ps1"
}

Write-Host "== CreatorPulse Dev ==" -ForegroundColor Cyan
Write-Host "后端: http://127.0.0.1:8001"
Write-Host "前端: http://127.0.0.1:5174"
Write-Host "按 Ctrl+C 停止全部进程"
Write-Host ""

$backend = Start-Process -PassThru -NoNewWindow -FilePath $backendPy -ArgumentList @(
    "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001", "--app-dir", "backend"
) -WorkingDirectory (Join-Path $Root "backend")

$frontend = Start-Process -PassThru -NoNewWindow -FilePath "pnpm" -ArgumentList @("dev") -WorkingDirectory (Join-Path $Root "frontend")

try {
    while ($true) {
        if ($backend.HasExited -or $frontend.HasExited) {
            Write-Host "某个进程已退出，正在清理..." -ForegroundColor Yellow
            break
        }
        Start-Sleep -Seconds 1
    }
}
finally {
    foreach ($p in @($backend, $frontend)) {
        if ($p -and -not $p.HasExited) {
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        }
    }
    # also kill children if any
    Get-Process -Name "node","uvicorn" -ErrorAction SilentlyContinue | Where-Object {
        $_.Path -like "*$Root*" -or $_.MainWindowTitle -like "*CreatorPulse*"
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "已停止。"
}
