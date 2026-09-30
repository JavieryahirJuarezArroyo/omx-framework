# Chat UI local (8501) — requiere ROS 2 sourcado y turtlesim en la misma red DDS.
# Para demo sin ROS en Windows: usa .\scripts\run-turtlesim-agent.ps1 (Docker).

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$env:ROS_AGENT_ROBOT = "turtlesim"
Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue

Write-Host "Arrancando agente (ROS 2 in-process). Chat: http://localhost:8501" -ForegroundColor Cyan
python -m agent.server
