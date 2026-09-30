# OMX-F follower + agente (Docker Ubuntu + ROS 2 Jazzy)
# Uso mock:  .\scripts\run-omx-follower-agent.ps1
# Hardware:   .\scripts\setup-omx-usb.ps1   (Admin, una vez por sesión USB)
#             .\scripts\run-omx-follower-agent.ps1 -Hardware -SkipBuild

param(
    [switch]$Hardware,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$chatPort = if ($env:ROS_AGENT_CHAT_PORT) { $env:ROS_AGENT_CHAT_PORT } else { "8503" }
$containerName = "omx-follower-run"
$envFile = Join-Path $Root "agent\.env"
$imageName = "omx-follower-agent"
$wslDistro = "docker-desktop"

if (-not (Test-Path $envFile)) {
    Write-Host "Falta agent\.env (GOOGLE_API_KEY, GROQ_API_KEY u OPENAI_API_KEY)" -ForegroundColor Red
    exit 1
}

if ($Hardware) {
    $env:OMX_USE_MOCK = "false"
}

$useMock = if ($env:OMX_USE_MOCK) { $env:OMX_USE_MOCK.ToLower() } else { "true" }
$serial = $env:OMX_SERIAL_DEVICE
if (-not $serial) { $serial = "" }

function Get-SerialInDockerVm {
    $dev = wsl -d $wslDistro sh -c "modprobe cdc_acm 2>/dev/null; ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null | tail -1" 2>$null
    return ($dev | Out-String).Trim()
}

function Test-UsbipdAttached {
    $list = usbipd list 2>$null | Out-String
    if ($list -match "2f5d:2202.*Attached") { return $true }
    if ($list -match "2f5d:2202.*Shared") { return $true }
    return $false
}

if ($useMock -eq "false") {
    if (-not $serial) {
        wsl -d $wslDistro sh -c "modprobe cdc_acm 2>/dev/null || true" | Out-Null
        Start-Sleep -Seconds 1
        $serial = Get-SerialInDockerVm
        if ($serial) {
            $env:OMX_SERIAL_DEVICE = $serial
            Write-Host "Auto serial: $serial" -ForegroundColor Cyan
        }
    }
    if (-not $serial) {
        Write-Host "Hardware real: no hay /dev/ttyACM* en Docker Desktop." -ForegroundColor Red
        Write-Host "1) Conecta el brazo (COM3 / VID 2f5d:2202)" -ForegroundColor Yellow
        Write-Host "2) Ejecuta como Admin: .\scripts\setup-omx-usb.ps1" -ForegroundColor Yellow
        Write-Host "3) Vuelve a correr: .\scripts\run-omx-follower-agent.ps1 -Hardware -SkipBuild" -ForegroundColor Yellow
        exit 1
    }
    if (-not (Test-UsbipdAttached)) {
        Write-Host "Aviso: usbipd no muestra el brazo como Shared/Attached. Si falla el bringup, usa setup-omx-usb.ps1 (Admin)." -ForegroundColor Yellow
    }
}

function Wait-Chat {
    param([int]$MaxSec = 180)
    for ($i = 0; $i -lt $MaxSec; $i++) {
        try {
            $r = Invoke-RestMethod -Uri "http://127.0.0.1:$chatPort/api/robot" -TimeoutSec 3
            if ($r.id -eq "open_manipulator_omx_f") { return $true }
        } catch { Start-Sleep -Seconds 3 }
    }
    return $false
}

docker rm -f $containerName 2>&1 | Out-Null

if (-not $SkipBuild) {
    Write-Host "Construyendo imagen $imageName (primera vez tarda bastante)..." -ForegroundColor Yellow
    docker build -f docker/omx-follower/Dockerfile -t $imageName .
} else {
    Write-Host "Skip build ($imageName)" -ForegroundColor Gray
}

$dockerEnv = @(
    "-e", "ROS_AGENT_ROBOT=open_manipulator_omx_f",
    "-e", "OMX_USE_MOCK=$useMock"
)
if ($serial) {
    $dockerEnv += @("-e", "OMX_SERIAL_DEVICE=$serial")
}

$deviceArgs = @()
if ($useMock -eq "false" -and $serial -match "^/dev/") {
    $deviceArgs = @("--device", "${serial}:${serial}")
}

Write-Host "Mock hardware: $useMock  Serial: $(if ($serial) { $serial } else { '(ninguno)' })" -ForegroundColor Cyan

docker run -d --name $containerName `
    --env-file $envFile `
    @dockerEnv `
    @deviceArgs `
    -p "${chatPort}:8501" `
    $imageName

if (-not (Wait-Chat)) {
    Write-Host "Agente no listo. Logs:" -ForegroundColor Red
    docker logs $containerName --tail 100
    exit 1
}

try {
    $st = Invoke-RestMethod "http://127.0.0.1:$chatPort/api/state" -TimeoutSec 25
    if ($st.arm) {
        Write-Host "joint_states OK: $($st.arm -join ', ')" -ForegroundColor Green
    } elseif ($st.error) {
        Write-Host "Estado: $($st.error)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Revisa docker logs $containerName" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Chat OMX: http://localhost:$chatPort" -ForegroundColor Cyan
if ($useMock -eq "true") {
    Write-Host "Modo MOCK (sin brazo). Hardware: .\scripts\setup-omx-usb.ps1 (Admin) luego -Hardware" -ForegroundColor Gray
} else {
    Write-Host "Modo HARDWARE (USB). Prueba: 'enciende torque' luego 'abre gripper' con cuidado." -ForegroundColor Green
}
