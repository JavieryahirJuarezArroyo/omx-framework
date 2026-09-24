#!/usr/bin/env python3
"""Bridge HTTP para ROS 2 turtlesim (contrato REST del framework).

Mapeo move_joints (3 valores):
  joints[0] = linear.x  (m/s)
  joints[1] = angular.z (rad/s)
  joints[2] = ignorado (pon 0)

GET /state arm = [x, y, theta] desde /turtle1/pose

Corre en el mismo entorno ROS 2 que turtlesim (Docker o host):
  pip install fastapi uvicorn
  python3 turtlesim_bridge.py
"""
from __future__ import annotations

import threading
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_srvs.srv import Empty
from turtlesim.msg import Pose

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

DEFAULT_SPAWN = (5.544445, 5.544445, 0.0)
LIMITS = {
    'linear_x': (-2.0, 2.0),
    'angular_z': (-2.0, 2.0),
}

app = FastAPI(title='turtlesim-bridge')
node: Node | None = None
publisher = None
reset_client = None
pose_lock = threading.Lock()
latest_pose = {'x': 0.0, 'y': 0.0, 'theta': 0.0, 'ready': False}


class MoveJoints(BaseModel):
    joints: list[float] = Field(min_length=2, max_length=6)
    seconds: float = 2.0


def _wait_future(fut, timeout: float) -> bool:
    t0 = time.time()
    while not fut.done() and (time.time() - t0) < timeout:
        time.sleep(0.05)
    return fut.done()


def on_pose(msg: Pose):
    with pose_lock:
        latest_pose['x'] = float(msg.x)
        latest_pose['y'] = float(msg.y)
        latest_pose['theta'] = float(msg.theta)
        latest_pose['ready'] = True


def arm_state() -> list[float]:
    with pose_lock:
        if not latest_pose['ready']:
            raise HTTPException(503, 'sin /turtle1/pose (¿turtlesim_node corriendo?)')
        return [latest_pose['x'], latest_pose['y'], latest_pose['theta']]


def validate_cmd(lin: float, ang: float):
    lo, hi = LIMITS['linear_x']
    if not (lo <= lin <= hi):
        raise HTTPException(400, f'linear_x={lin} fuera de [{lo},{hi}]')
    lo, hi = LIMITS['angular_z']
    if not (lo <= ang <= hi):
        raise HTTPException(400, f'angular_z={ang} fuera de [{lo},{hi}]')


def publish_twist(lin: float, ang: float, duration: float):
    validate_cmd(lin, ang)
    twist = Twist()
    twist.linear.x = float(lin)
    twist.angular.z = float(ang)
    deadline = time.time() + max(0.1, duration)
    rate_hz = 10.0
    while time.time() < deadline:
        publisher.publish(twist)
        time.sleep(1.0 / rate_hz)
    stop = Twist()
    publisher.publish(stop)


@app.get('/health')
def health():
    with pose_lock:
        ready = latest_pose['ready']
    return {'ok': True, 'has_pose': ready}


@app.get('/state')
def state():
    return {'arm': arm_state()}


@app.post('/move_joints')
def move_joints(m: MoveJoints):
    lin = float(m.joints[0])
    ang = float(m.joints[1]) if len(m.joints) > 1 else 0.0
    publish_twist(lin, ang, m.seconds)
    return {'ok': True, 'linear_x': lin, 'angular_z': ang, 'seconds': m.seconds}


@app.post('/home')
def home():
    if reset_client is None or not reset_client.service_is_ready():
        raise HTTPException(503, 'servicio /reset no disponible')
    fut = reset_client.call_async(Empty.Request())
    if not _wait_future(fut, 5.0):
        raise HTTPException(504, 'timeout /reset')
    time.sleep(0.3)
    return {'ok': True, 'arm': arm_state()}


@app.post('/init')
def init():
    return home()


@app.post('/gripper')
def gripper_unsupported():
    raise HTTPException(501, 'turtlesim no tiene gripper')


@app.post('/torque')
def torque_unsupported():
    raise HTTPException(501, 'no aplica en turtlesim')


def main():
    global node, publisher, reset_client
    rclpy.init()
    node = Node('turtlesim_http_bridge')
    node.create_subscription(Pose, '/turtle1/pose', on_pose, 10)
    publisher = node.create_publisher(Twist, '/turtle1/cmd_vel', 10)
    reset_client = node.create_client(Empty, '/reset')
    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()
    for _ in range(50):
        if latest_pose['ready']:
            break
        time.sleep(0.1)
    print('turtlesim bridge :8000 (necesita turtlesim_node)', flush=True)
    uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info')


if __name__ == '__main__':
    main()
