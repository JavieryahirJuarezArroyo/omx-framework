# Turtlesim listo para probar: bridge Docker :18000 + chat agente :8501
# Uso (desde raíz del repo):  .\scripts\run-turtlesim-agent.ps1
# Si el bridge no está arriba:  docker start omx-turtlesim-run
#   o crea el contenedor: ver docs/turtlesim.md / docker/turtlesim/

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$bridgePort = if ($env:ROS_AGENT_BRIDGE_PORT) { $env:ROS_AGENT_BRIDGE_PORT } else { "18000" }
$bridgeUrl = "http://127.0.0.1:$bridgePort"

function Wait-Bridge {
    param([int]$MaxSec = 30)
    for ($i = 0; $i -lt $MaxSec; $i++) {
        try {
            $h = Invoke-RestMethod -Uri "$bridgeUrl/health" -TimeoutSec 2
            if ($h.ok) { return $true }
        } catch { Start-Sleep -Seconds 1 }
    }
    return $false
}

if (-not (Wait-Bridge)) {
    Write-Host "Bridge no responde en $bridgeUrl" -ForegroundColor Red
    Write-Host "Intenta: docker start omx-turtlesim-run" -ForegroundColor Yellow
    Write-Host "O crea contenedor (headless): docker build -f docker/turtlesim/Dockerfile -t omx-turtlesim ."
    Write-Host "  docker run -d --name omx-turtlesim-run -p ${bridgePort}:8000 omx-turtlesim"
    exit 1
}

$st = Invoke-RestMethod "$bridgeUrl/state"
Write-Host "Bridge OK. Pose: $($st.arm -join ', ')" -ForegroundColor Green

Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 1

Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
$env:ROS_AGENT_ROBOT = "turtlesim"
$env:ROS_AGENT_BRIDGE = $bridgeUrl

# Comprobar tools generadas (sin arrancar servidor completo)
python -c @"
from agent.context import reload
from agent.tools_lc import get_agent_tools
import os
os.environ['ROS_AGENT_ROBOT']='turtlesim'
os.environ['ROS_AGENT_BRIDGE']='$bridgeUrl'
reload()
print('Tools:', [t.name for t in get_agent_tools()])
"@

Write-Host ""
Write-Host "Chat: http://localhost:8501" -ForegroundColor Cyan
Write-Host "Prueba: '¿cuál es tu posición?' o 'avanza 1 metro recto'" -ForegroundColor Cyan
python -m agent.server
