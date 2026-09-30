# Tras desconectar/reconectar USB o modo seguridad Dynamixel:
# 1) Re-adjuntar USB (Admin)  2) Reiniciar contenedor  3) reboot + torque ON
#
# Uso (Admin primero si usbipd no está Attached):
#   .\scripts\setup-omx-usb.ps1
#   .\scripts\reinit-omx-hardware.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

& "$Root\scripts\run-omx-follower-agent.ps1" -Hardware -SkipBuild

Write-Host "Reiniciando servos Dynamixel (reboot_dxl)..." -ForegroundColor Yellow
docker exec omx-follower-run bash -lc @'
source /opt/ros/jazzy/setup.bash
source /ros2_ws/install/setup.bash
ros2 service call /dynamixel_hardware_interface/reboot_dxl dynamixel_interfaces/srv/RebootDxl '{}' || true
sleep 2
ros2 service call /dynamixel_hardware_interface/set_dxl_torque std_srvs/srv/SetBool "{data: true}"
'@

Write-Host "Listo. Chat: http://localhost:8503 - prueba estado o ve a init despacio" -ForegroundColor Green
