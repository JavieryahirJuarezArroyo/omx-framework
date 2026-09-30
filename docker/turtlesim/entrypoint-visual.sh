#!/bin/bash
set -e
source /opt/ros/humble/setup.bash
cd /workspace/omx-framework
export ROS_AGENT_ROBOT=turtlesim
ros2 run turtlesim turtlesim_node &
sleep 3
exec python3 -m agent.server
