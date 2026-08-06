@echo off
title CreatorPulse Launcher
cd /d "%~dp0"

echo.
echo   ========================================
echo     CreatorPulse
echo   ========================================
echo   Starting, please wait...
echo.

set "CREATORPULSE_ROOT=%~dp0"
where pwsh.exe >nul 2>&1
if not errorlevel 1 (
  pwsh.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1"
) else (
  rem Windows PowerShell 5.1 misreads UTF-8 scripts without a BOM. Decode explicitly.
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
    "$path=Join-Path $env:CREATORPULSE_ROOT 'scripts\start.ps1'; $text=[Text.Encoding]::UTF8.GetString([IO.File]::ReadAllBytes($path)); Invoke-Expression $text"
)
set ERR=%ERRORLEVEL%

if not "%ERR%"=="0" (
  echo.
  echo   Startup failed. Please save the messages above.
  pause
  exit /b 1
)

exit /b 0
