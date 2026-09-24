#!/bin/bash
set -e
source /opt/ros/humble/setup.bash
# Requiere DISPLAY (VcXsrv en Windows: host.docker.internal:0.0)
ros2 run turtlesim turtlesim_node &
sleep 3
exec python3 /workspace/turtlesim_bridge.py
