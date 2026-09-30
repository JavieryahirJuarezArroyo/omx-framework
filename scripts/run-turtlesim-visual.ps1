# Ventana nativa turtlesim + agente (Windows + Docker Desktop + VcXsrv)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

docker build -f docker/turtlesim/Dockerfile -t omx-turtlesim .
docker run --rm -it -e DISPLAY=host.docker.internal:0 -p 8501:8501 omx-turtlesim `
  /bin/bash -c "source /opt/ros/humble/setup.bash; ros2 run turtlesim turtlesim_node & sleep 3; cd /workspace/omx-framework; export ROS_AGENT_ROBOT=turtlesim; exec python3 -m agent.server"
