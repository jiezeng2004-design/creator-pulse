# CreatorPulse 一键启动：双击后后台常驻，可关闭本窗口
$ErrorActionPreference = "Continue"
$Root = if ($env:CREATORPULSE_ROOT) {
    $env:CREATORPULSE_ROOT.TrimEnd('\')
} else {
    Split-Path -Parent $PSScriptRoot
}
Set-Location $Root
$Data = Join-Path $Root "data"
New-Item -ItemType Directory -Force -Path $Data | Out-Null

$CpDesktopBoot = $env:CREATORPULSE_DESKTOP_BOOT

function Get-CurrentDesktopName {
    Add-Type -TypeDefinition @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class CpDesktopProbe {
    [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
    [DllImport("user32.dll")] public static extern IntPtr GetThreadDesktop(uint dwThreadId);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern bool GetUserObjectInformation(IntPtr hObj, int nIndex, StringBuilder pvInfo, int nLength, out int lpnLengthNeeded);
}
"@ -ErrorAction SilentlyContinue
    try {
        $tid = [CpDesktopProbe]::GetCurrentThreadId()
        $h = [CpDesktopProbe]::GetThreadDesktop($tid)
        $sb = New-Object System.Text.StringBuilder 256
        $needed = 0
        if ([CpDesktopProbe]::GetUserObjectInformation($h, 2, $sb, 256, [ref]$needed)) {
            return $sb.ToString()
        }
    } catch {}
    return $null
}

function Ensure-UserDesktop {
    $current = Get-CurrentDesktopName
    if ($null -eq $current -or $current -eq "Default" -or $CpDesktopBoot -eq "1") {
        return
    }
    Write-Host ""
    Write-Host "  当前运行在非交互桌面（$current），尝试切换到用户桌面启动…" -ForegroundColor Yellow
    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class CpDesktopBoot {
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct STARTUPINFO {
        public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
        public int dwX; public int dwY; public int dwXSize; public int dwYSize; public int dwXCountChars;
        public int dwYCountChars; public int dwFillAttribute; public int dwFlags;
        public short wShowWindow; public short cbReserved2; public IntPtr lpReserved2;
        public IntPtr hStdInput; public IntPtr hStdOutput; public IntPtr hStdError;
    }
    [StructLayout(LayoutKind.Sequential)]
    public struct PROCESS_INFORMATION {
        public IntPtr hProcess; public IntPtr hThread; public int dwProcessId; public int dwThreadId;
    }
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern bool CreateProcess(
        string lpApplicationName, string lpCommandLine,
        IntPtr lpProcessAttributes, IntPtr lpThreadAttributes, bool bInheritHandles,
        uint dwCreationFlags, IntPtr lpEnvironment, string lpCurrentDirectory,
        ref STARTUPINFO lpStartupInfo, out PROCESS_INFORMATION lpProcessInformation);
}
"@ -ErrorAction SilentlyContinue
    $selfPath = (Get-Process -Id $PID).Path
    if (-not $selfPath) { return }
    $si = New-Object CpDesktopBoot+STARTUPINFO
    $si.cb = [System.Runtime.InteropServices.Marshal]::SizeOf([type][CpDesktopBoot+STARTUPINFO])
    $si.lpDesktop = "WinSta0\Default"
    $pi = New-Object CpDesktopBoot+PROCESS_INFORMATION
    $scriptPath = Join-Path $PSScriptRoot "start.ps1"
    $cmdLine = "`"$selfPath`" -NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
    $env:CREATORPULSE_DESKTOP_BOOT = "1"
    $ok = [CpDesktopBoot]::CreateProcess(
        $null, $cmdLine, [IntPtr]::Zero, [IntPtr]::Zero, $false, 0,
        [IntPtr]::Zero, $Root, [ref]$si, [ref]$pi)
    if ($ok) {
        Write-Host "  已在用户桌面重新启动，请等待窗口自动完成启动。" -ForegroundColor Green
        exit 0
    }
    Write-Host "  无法切换到用户桌面（错误码 $([System.Runtime.InteropServices.Marshal]::GetLastWin32Error())）。" -ForegroundColor Red
    Write-Host "  浏览器登录窗口可能无法正常显示；请在正常桌面双击「启动 CreatorPulse.bat」。" -ForegroundColor Yellow
}

Ensure-UserDesktop

function Test-Listening([int]$Port) {
    try {
        return $null -ne (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    } catch { return $false }
}

function Wait-Url([string]$Url, [int]$Seconds = 50) {
    $end = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $end) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) { return $true }
        } catch {}
        Start-Sleep -Milliseconds 400
    }
    return $false
}

function Get-PnpmCmd {
    foreach ($cand in @(
        (Join-Path $env:APPDATA "npm\pnpm.cmd"),
        (Join-Path $env:ProgramFiles "nodejs\pnpm.cmd")
    )) {
        if (Test-Path $cand) { return $cand }
    }
    foreach ($name in @("pnpm.cmd", "pnpm.exe", "pnpm")) {
        $c = Get-Command $name -ErrorAction SilentlyContinue
        if ($c) { return $c.Source }
    }

    return $null
}
Write-Host ""
Write-Host "  ======================================" -ForegroundColor Cyan
Write-Host "   CreatorPulse 一键启动" -ForegroundColor Cyan
Write-Host "  ======================================" -ForegroundColor Cyan
Write-Host "  目录: $Root"
Write-Host ""

# Already running → just open browser
if ((Test-Listening 8001) -and (Test-Listening 5174)) {
    Write-Host "  [OK] 服务已在运行，正在打开网页…" -ForegroundColor Green
    Start-Process "http://127.0.0.1:5174"
    Write-Host ""
    Write-Host "  打开: http://127.0.0.1:5174" -ForegroundColor Green
    Write-Host "  总览里「未连接」= 平台账号未登录，不是软件没启动。" -ForegroundColor Yellow
    Write-Host "  请到左侧「账号」里连接/登录/同步。" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  可关闭本窗口，服务会继续运行。"
    Write-Host "  停止请双击: 停止 CreatorPulse.bat"
    Write-Host ""
    Start-Sleep -Seconds 6
    exit 0
}

$py = Join-Path $Root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $py) -or -not (Test-Path (Join-Path $Root "frontend\node_modules"))) {
    Write-Host "  首次使用，自动安装依赖（可能需几分钟）…" -ForegroundColor Yellow
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Host "  缺少 Python。请安装 Python 3.12+ 并勾选 Add to PATH。" -ForegroundColor Red
        pause; exit 1
    }
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Write-Host "  缺少 Node.js。请安装 Node.js 18+。" -ForegroundColor Red
        pause; exit 1
    }
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { python -m pip install uv -q }
    if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) { npm install -g pnpm }
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root "scripts\setup.ps1")
    if (-not (Test-Path $py)) {
        Write-Host "  安装失败，请把窗口内容截图发给助手。" -ForegroundColor Red
        pause; exit 1
    }
}

if (-not (Test-Path (Join-Path $Root "backend\.env"))) {
    Copy-Item (Join-Path $Root "backend\.env.example") (Join-Path $Root "backend\.env")
}

Write-Host "  启动后端…"
$backendOut = Join-Path $Data "backend.out.log"
$backendErr = Join-Path $Data "backend.err.log"
$backend = Start-Process -PassThru -WindowStyle Hidden -FilePath $py -ArgumentList @(
    "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001"
) -WorkingDirectory (Join-Path $Root "backend") `
  -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr

$pnpmCmd = Get-PnpmCmd
if (-not $pnpmCmd) {
    Write-Host "  未找到 pnpm，请先安装 pnpm" -ForegroundColor Red
    pause; exit 1
}

Write-Host "  启动前端…"
$frontendOut = Join-Path $Data "frontend.out.log"
$frontendErr = Join-Path $Data "frontend.err.log"
$frontend = Start-Process -PassThru -WindowStyle Hidden -FilePath "cmd.exe" -ArgumentList @(
    "/c", "`"$pnpmCmd`" dev --host 127.0.0.1 --port 5174"
) -WorkingDirectory (Join-Path $Root "frontend") `
  -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr

# Persist PIDs for stop script (services keep running after this window closes)
@"
backend=$($backend.Id)
frontend=$($frontend.Id)
started=$(Get-Date -Format o)
"@ | Set-Content -Path (Join-Path $Data "pids.txt") -Encoding UTF8

Write-Host "  等待就绪…"
$okB = Wait-Url "http://127.0.0.1:8001/api/health" 50
$okF = Wait-Url "http://127.0.0.1:5174" 50

if (-not $okB) {
    Write-Host "  后端失败，日志 data\backend.err.log:" -ForegroundColor Red
    Get-Content $backendErr -ErrorAction SilentlyContinue | Select-Object -Last 15
}
if (-not $okF) {
    Write-Host "  前端失败，日志 data\frontend.err.log:" -ForegroundColor Red
    Get-Content $frontendErr -ErrorAction SilentlyContinue | Select-Object -Last 15
}

if ($okB -and $okF) {
    Write-Host ""
    Write-Host "  [成功] 已启动并打开浏览器" -ForegroundColor Green
    Write-Host "  地址: http://127.0.0.1:5174" -ForegroundColor Green
    Write-Host ""
    Write-Host "  重要说明:" -ForegroundColor Yellow
    Write-Host "  · 软件已运行，可关闭本黑窗口，服务继续后台运行"
    Write-Host "  · 总览「未连接」= 平台账号还没登录，不是启动失败"
    Write-Host "  · 请点左侧「账号」→ 对知乎点「打开登录」→ 登录后「检查并同步」"
    Write-Host "  · 停止服务：双击「停止 CreatorPulse.bat」"
    Write-Host ""
    Start-Process "http://127.0.0.1:5174"
    Start-Sleep -Seconds 8
    exit 0
}

Write-Host "  启动未完成。请截图本窗口。" -ForegroundColor Red
pause
exit 1
