# CreatorPulse Windows setup script
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "== CreatorPulse Setup ==" -ForegroundColor Cyan

function Assert-Command($Name, $Hint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "未找到命令: $Name。$Hint"
    }
}

Write-Host "[1/8] 检查 Python..."
Assert-Command python "请安装 Python 3.12+"
$pyVer = python --version
Write-Host "  $pyVer"

Write-Host "[2/8] 检查 uv..."
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "  安装 uv..."
    python -m pip install uv
}
Assert-Command uv "请安装 uv: pip install uv"
Write-Host "  $(uv --version)"

Write-Host "[3/8] 检查 Node.js..."
Assert-Command node "请安装 Node.js 18+"
Write-Host "  $(node --version)"

Write-Host "[4/8] 检查 pnpm..."
if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
    Write-Host "  安装 pnpm..."
    npm install -g pnpm
}
Assert-Command pnpm "请安装 pnpm: npm i -g pnpm"
Write-Host "  $(pnpm --version)"

Write-Host "[5/8] 创建本地目录..."
New-Item -ItemType Directory -Force -Path "$Root\data", "$Root\browser-profiles" | Out-Null
if (-not (Test-Path "$Root\backend\.env")) {
    Copy-Item "$Root\backend\.env.example" "$Root\backend\.env"
    Write-Host "  已复制 backend/.env.example -> backend/.env"
} else {
    Write-Host "  已存在 backend/.env，跳过覆盖"
}

Write-Host "[6/8] 安装后端依赖..."
Set-Location "$Root\backend"
if (-not (Test-Path ".venv")) {
    uv venv .venv
}
uv pip install -e ".[dev]"
Write-Host "  安装 Playwright Chromium..."
& "$Root\backend\.venv\Scripts\python.exe" -m playwright install chromium

Write-Host "[7/8] 初始化数据库..."
& "$Root\backend\.venv\Scripts\python.exe" -c "import asyncio; from app.db.session import init_db; asyncio.run(init_db()); print('DB ready')"

Write-Host "[8/8] 安装前端依赖..."
Set-Location "$Root\frontend"
# pnpm 10+ blocks dependency build scripts until approved (esbuild for Vite)
pnpm install
if ($LASTEXITCODE -ne 0) {
    pnpm approve-builds --all
    pnpm install
}

Set-Location $Root
Write-Host ""
Write-Host "Setup 完成。" -ForegroundColor Green
Write-Host "启动开发环境: .\scripts\dev.ps1"
Write-Host "运行测试:     .\scripts\test.ps1"
