# Chat UI (8501) + turtlesim bridge (18000). Ejecutar desde la raíz del repo.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$bridgePort = 18000
try {
    $null = Invoke-WebRequest -Uri "http://127.0.0.1:$bridgePort/health" -UseBasicParsing -TimeoutSec 2
} catch {
    Write-Host "Bridge no responde en :$bridgePort. Levanta Docker: docker start omx-turtlesim-run" -ForegroundColor Yellow
    exit 1
}

Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 1

Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
$env:ROS_AGENT_ROBOT = "turtlesim"
$env:ROS_AGENT_BRIDGE = "http://127.0.0.1:$bridgePort"

Write-Host "Abre http://localhost:8501 (Ctrl+C para detener)" -ForegroundColor Green
python -m agent.server
