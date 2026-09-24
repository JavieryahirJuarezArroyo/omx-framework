# Ventana nativa turtlesim + bridge (Windows + Docker Desktop + VcXsrv)
# 1) Instala VcXsrv y arranca "XLaunch" con "Disable access control"
# 2) Ejecuta: .\scripts\run-turtlesim-visual.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
if (-not (Test-Path "$Root\bridge\turtlesim_bridge.py")) {
    $Root = (Get-Location).Path
}
Set-Location $Root

docker build -f docker/turtlesim/Dockerfile -t omx-turtlesim .
docker rm -f omx-turtlesim-visual 2>$null | Out-Null

$port = if ($env:ROS_AGENT_BRIDGE_PORT) { $env:ROS_AGENT_BRIDGE_PORT } else { "18000" }

docker run -d --name omx-turtlesim-visual `
  -p "${port}:8000" `
  -e DISPLAY=host.docker.internal:0.0 `
  -e QT_X11_NO_MITSHM=1 `
  omx-turtlesim /bin/bash -c "sed -i 's/\r$//' /entrypoint.sh 2>/dev/null; source /opt/ros/humble/setup.bash; ros2 run turtlesim turtlesim_node & sleep 3; exec python3 /workspace/turtlesim_bridge.py"

Write-Host "Bridge: http://localhost:$port"
Write-Host "UI:     ROS_AGENT_ROBOT=turtlesim ROS_AGENT_BRIDGE=http://localhost:$port python -m agent.server"
Write-Host "Abre http://localhost:8501 — veras el mapa 2D en la pagina; la ventana azul requiere VcXsrv."
