#!/bin/bash
set -e
source /opt/ros/humble/setup.bash
cd /workspace/omx-framework
export ROS_AGENT_ROBOT=turtlesim

# Simulación sin ventana (Xvfb); la UI web dibuja la tortuga en el canvas del chat.
xvfb-run -a ros2 run turtlesim turtlesim_node &
TURTLE_PID=$!
sleep 2

echo "Esperando /turtle1/pose..." >&2
for i in $(seq 1 30); do
  if ros2 topic echo /turtle1/pose --once --spin-time 2 >/dev/null 2>&1; then
    echo "turtlesim listo" >&2
    break
  fi
  sleep 1
done

exec python3 -m agent.server
