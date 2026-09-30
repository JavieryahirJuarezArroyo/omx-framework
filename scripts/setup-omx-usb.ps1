# Pasa el USB ROBOTIS (OMX, VID 2f5d:2202 / COM3) a la VM de Docker Desktop.
# Requiere ejecutar como Administrador (clic derecho → Run with PowerShell as admin).
#
# Uso (Admin):
#   .\scripts\setup-omx-usb.ps1
# Luego (usuario normal):
#   .\scripts\run-omx-follower-agent.ps1 -Hardware

$ErrorActionPreference = "Stop"
$vidPid = "2f5d:2202"
$wslDistro = "docker-desktop"

$usbipd = Get-Command usbipd -ErrorAction SilentlyContinue
if (-not $usbipd) {
    Write-Host "Instala usbipd-win: winget install dorssel.usbipd-win" -ForegroundColor Red
    exit 1
}

$line = usbipd list | Select-String $vidPid
if (-not $line) {
    Write-Host "No se ve el brazo USB ($vidPid). Revisa cable y COM3 en Windows." -ForegroundColor Red
    exit 1
}

$busid = ($line -split '\s+')[0].Trim()
Write-Host "Dispositivo: BUSID=$busid  ($vidPid)" -ForegroundColor Cyan

usbipd bind --busid $busid
usbipd attach --wsl $wslDistro --busid $busid

Start-Sleep -Seconds 2
wsl -d $wslDistro sh -c "modprobe cdc_acm 2>/dev/null || true"
Start-Sleep -Seconds 1
    $dev = wsl -d $wslDistro sh -c "ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null | tail -1"
if (-not $dev) {
    Write-Host "USB adjunto pero no hay /dev/ttyACM* en $wslDistro. Reintenta attach o reinicia Docker Desktop." -ForegroundColor Yellow
    exit 1
}

Write-Host "Serial en Docker VM: $dev" -ForegroundColor Green
Write-Host ""
Write-Host "Siguiente paso (PowerShell normal):" -ForegroundColor Cyan
Write-Host "  cd omx-framework" -ForegroundColor White
Write-Host "  `$env:OMX_SERIAL_DEVICE = '$dev'" -ForegroundColor White
Write-Host "  .\scripts\run-omx-follower-agent.ps1 -Hardware -SkipBuild" -ForegroundColor White
