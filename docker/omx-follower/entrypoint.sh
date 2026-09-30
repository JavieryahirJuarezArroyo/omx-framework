#!/bin/bash
set -e
source /opt/ros/jazzy/setup.bash
source /ros2_ws/install/setup.bash

cd /workspace/omx-framework
export ROS_AGENT_ROBOT="${ROS_AGENT_ROBOT:-open_manipulator_omx_f}"

USE_MOCK="${OMX_USE_MOCK:-true}"
SERIAL="${OMX_SERIAL_DEVICE:-}"
if [ "$USE_MOCK" = "false" ] && [ -z "$SERIAL" ]; then
  SERIAL="/dev/ttyACM0"
fi
LAUNCH_PKG="open_manipulator_bringup"
LAUNCH_FILE=""
for candidate in omx_f.launch.py omx_f_follower_ai.launch.py open_manipulator_x.launch.py; do
  if [ -f "/ros2_ws/install/${LAUNCH_PKG}/share/${LAUNCH_PKG}/launch/${candidate}" ]; then
    LAUNCH_FILE="$candidate"
    break
  fi
done
if [ -z "$LAUNCH_FILE" ]; then
  echo "ERROR: no se encontró launch OMX en ${LAUNCH_PKG}" >&2
  exit 1
fi
echo "Launch: ${LAUNCH_PKG}/${LAUNCH_FILE}" >&2

echo "OMX follower bringup (mock=$USE_MOCK serial=${SERIAL:-none})" >&2

LAUNCH_ARGS=(use_mock_hardware:="${USE_MOCK}" start_rviz:=false)
if [ "$USE_MOCK" = "false" ] && [ -n "$SERIAL" ]; then
  LAUNCH_ARGS+=(port_name:="${SERIAL}")
fi

ros2 launch "${LAUNCH_PKG}" "${LAUNCH_FILE}" "${LAUNCH_ARGS[@]}" &
BRINGUP_PID=$!

cleanup() {
  kill "$BRINGUP_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "Esperando /joint_states..." >&2
MAX_WAIT=60
if [ "$USE_MOCK" = "false" ]; then
  MAX_WAIT=120
fi
for i in $(seq 1 $MAX_WAIT); do
  if ros2 topic echo /joint_states --once --spin-time 2 >/dev/null 2>&1; then
    echo "Brazo listo (joint_states OK)" >&2
    break
  fi
  if ! kill -0 "$BRINGUP_PID" 2>/dev/null; then
    echo "ERROR: bringup terminó antes de publicar joint_states" >&2
    exit 1
  fi
  sleep 2
done

exec python3 -m agent.server
