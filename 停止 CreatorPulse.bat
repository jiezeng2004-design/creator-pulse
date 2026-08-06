@echo off
chcp 65001 >nul
title 停止 CreatorPulse
cd /d "%~dp0"
echo.
echo   正在停止 CreatorPulse…
where pwsh.exe >nul 2>&1
if not errorlevel 1 (
  pwsh.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop.ps1"
) else (
  rem Windows PowerShell 5.1 misreads UTF-8 scripts without a BOM. Decode explicitly.
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
    "$path='%~dp0scripts\stop.ps1'; $text=[Text.Encoding]::UTF8.GetString([IO.File]::ReadAllBytes($path)); Invoke-Expression $text"
)
echo.
echo   可以关闭本窗口。
timeout /t 3 >nul
