# Recupera servos Dynamixel (LED rojo parpadeando) en omx-follower-run.
# Uso: .\scripts\recover-omx-servos.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not (docker ps -q -f name=omx-follower-run)) {
    Write-Host "No hay contenedor omx-follower-run. Ejecuta run-omx-follower-agent.ps1 -Hardware" -ForegroundColor Red
    exit 1
}

function Invoke-OmxRos {
    param([string]$RosCall)
    docker exec omx-follower-run bash -lc "source /opt/ros/jazzy/setup.bash && source /ros2_ws/install/setup.bash && $RosCall"
}

Write-Host "=== Torque OFF ===" -ForegroundColor Cyan
Invoke-OmxRos "ros2 service call /dynamixel_hardware_interface/set_dxl_torque std_srvs/srv/SetBool '{data: false}'"
Start-Sleep -Seconds 2

Write-Host "=== Reboot Dynamixel (todos los IDs del bus) ===" -ForegroundColor Cyan
Invoke-OmxRos "ros2 service call /dynamixel_hardware_interface/reboot_dxl dynamixel_interfaces/srv/RebootDxl '{}'"
Start-Sleep -Seconds 5

Write-Host "=== Torque ON ===" -ForegroundColor Cyan
Invoke-OmxRos "ros2 service call /dynamixel_hardware_interface/set_dxl_torque std_srvs/srv/SetBool '{data: true}'"
Start-Sleep -Seconds 1

Write-Host "=== Scan IDs 11-16 ===" -ForegroundColor Cyan
foreach ($id in 11, 12, 13, 14, 15, 16) {
    $out = Invoke-OmxRos "ros2 service call /dynamixel_hardware_interface/get_dxl_data dynamixel_interfaces/srv/GetDataFromDxl '{id: $id, item_name: Present_Position, timeout_sec: 2.0}' 2>&1"
    if ($out -match "result=True") {
        Write-Host "  ID ${id}: OK" -ForegroundColor Green
    } else {
        Write-Host "  ID ${id}: sin respuesta (error hardware o bus)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Si siguen parpadeando en ROJO:" -ForegroundColor Yellow
Write-Host "  - Apaga la fuente 12V del brazo 10 s y enciende de nuevo" -ForegroundColor Yellow
Write-Host "  - Quita carga mecanica (no fuerces el joint; joint4 suele ser el problematico)" -ForegroundColor Yellow
Write-Host "  - Admin: setup-omx-usb.ps1  luego  reinit-omx-hardware.ps1" -ForegroundColor Yellow
Write-Host "  - Ultimo recurso: Dynamixel Wizard en Windows (desconecta USB de Docker antes)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Chat: http://localhost:8503" -ForegroundColor Cyan
