# CreatorPulse 停止脚本：通过监听端口定位进程并停止。
# Get-NetTCPConnection 在本机可能返回“拒绝访问”，这里用 netstat 解析，
# 与 start.ps1 的启动方式互补，保证双击停止脚本始终有效。
$ErrorActionPreference = "Continue"
$Ports = @(8001, 5174)
$Targets = @()

foreach ($port in $Ports) {
    $line = netstat -ano -p tcp | Select-String "127.0.0.1:$port\s" |
        Where-Object { $_.Line -match "LISTENING" } |
        Select-Object -First 1
    if ($line) {
        $parts = ($line.ToString().Trim() -split "\s+")
        $procId = $parts[$parts.Count - 1]
        if ($procId -match "^\d+$" -and $procId -notin $Targets) {
            $Targets += $procId
        }
    }
}

if ($Targets.Count -eq 0) {
    Write-Host "  没有检测到运行中的 CreatorPulse（8001 / 5174 未监听）。" -ForegroundColor Yellow
} else {
    foreach ($procId in $Targets) {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($proc) {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            Write-Host "  已停止进程 $procId（$($proc.ProcessName)）" -ForegroundColor Green
        }
    }
    Start-Sleep -Milliseconds 800
    $still = @()
    foreach ($port in $Ports) {
        $line = netstat -ano -p tcp | Select-String "127.0.0.1:$port\s" |
            Where-Object { $_.Line -match "LISTENING" } |
            Select-Object -First 1
        if ($line) { $still += $port }
    }
    if ($still.Count -gt 0) {
        Write-Host "  端口 $($still -join ', ') 仍在监听，请稍候重试。" -ForegroundColor Red
    } else {
        Write-Host "  已停止，8001 / 5174 端口已释放。" -ForegroundColor Green
    }
}
