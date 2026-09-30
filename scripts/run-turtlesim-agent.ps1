# Turtlesim + agente ROS 2 en Docker (chat :8501)
# Uso (desde raíz del repo):  .\scripts\run-turtlesim-agent.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$chatPort = if ($env:ROS_AGENT_CHAT_PORT) { $env:ROS_AGENT_CHAT_PORT } else { "8502" }
$containerName = "omx-turtlesim-run"
$envFile = Join-Path $Root "agent\.env"

if (-not (Test-Path $envFile)) {
    Write-Host "Falta agent\.env (copia agent\.env.example y pon GROQ_API_KEY u OPENAI_API_KEY)" -ForegroundColor Red
    exit 1
}

function Wait-Chat {
    param([int]$MaxSec = 90)
    for ($i = 0; $i -lt $MaxSec; $i++) {
        try {
            $r = Invoke-RestMethod -Uri "http://127.0.0.1:$chatPort/api/robot" -TimeoutSec 3
            if ($r.id) { return $true }
        } catch { Start-Sleep -Seconds 2 }
    }
    return $false
}

$running = docker ps --filter "name=$containerName" --format "{{.Names}}" 2>$null
if ($running) {
    $mapped = docker port $containerName 8501/tcp 2>$null
    if ($mapped -notmatch ":$chatPort") {
        Write-Host "Recreando contenedor en puerto $chatPort..." -ForegroundColor Yellow
        docker rm -f $containerName | Out-Null
        $running = $null
    }
}
if (-not $running) {
    Write-Host "Construyendo imagen (incluye agent/.env para el LLM)..." -ForegroundColor Yellow
    docker build -f docker/turtlesim/Dockerfile -t omx-turtlesim .
    docker run -d --name $containerName --env-file $envFile -p "${chatPort}:8501" omx-turtlesim
} else {
    Write-Host "Contenedor $containerName ya corre. Si cambiaste código: docker rm -f $containerName y vuelve a ejecutar este script." -ForegroundColor Gray
}

if (-not (Wait-Chat)) {
    Write-Host "Agente no responde en http://127.0.0.1:$chatPort" -ForegroundColor Red
    Write-Host "Logs: docker logs $containerName" -ForegroundColor Yellow
    exit 1
}

try {
    $st = Invoke-RestMethod "http://127.0.0.1:$chatPort/api/state" -TimeoutSec 15
    if ($st.error) {
        Write-Host "ROS aún sin pose: $($st.error)" -ForegroundColor Yellow
    } else {
        Write-Host "Pose OK: $($st.arm -join ', ')" -ForegroundColor Green
    }
} catch {
    Write-Host "No se pudo leer /api/state (revisa docker logs)" -ForegroundColor Yellow
}

$info = Invoke-RestMethod "http://127.0.0.1:$chatPort/api/robot"
Write-Host "Robot: $($info.display_name) adapter=$($info.adapter)" -ForegroundColor Green

Write-Host ""
Write-Host "Chat: http://localhost:$chatPort" -ForegroundColor Cyan
Write-Host "(Si :8501 muestra 'bridge' antiguo, cierra python en ese puerto o usa ROS_AGENT_CHAT_PORT=8502)" -ForegroundColor Gray
Write-Host "Deberías ver cuadrícula + tortuga (verde=ROS ok, gris=sin pose)." -ForegroundColor Cyan
Write-Host "Ventana Qt clásica de turtlesim: .\scripts\run-turtlesim-visual.ps1 (VcXsrv)" -ForegroundColor Gray
