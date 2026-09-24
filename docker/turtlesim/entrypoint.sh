#!/bin/bash
set -e
source /opt/ros/humble/setup.bash
xvfb-run -a ros2 run turtlesim turtlesim_node &
sleep 4
exec python3 /workspace/turtlesim_bridge.py
