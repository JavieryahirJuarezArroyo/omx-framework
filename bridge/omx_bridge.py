#!/usr/bin/env python3
"""OMX-F bridge: ROS2 Jazzy (zenoh) -> HTTP.
Corre DENTRO del container open_manipulator en /workspace.
  python3 /workspace/omx_bridge.py  (puerto 8000, host network)

Endpoints (tools):
  GET  /health
  GET  /state
  POST /move_joints {"joints":[j1..j5], "seconds":4.0}
  POST /home | POST /init
  POST /gripper {"open":0.0..1.0, "seconds":2.0}
  POST /torque {"on":true}
  POST /reboot
"""
import threading
import time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from sensor_msgs.msg import JointState
from control_msgs.action import FollowJointTrajectory, GripperCommand
from trajectory_msgs.msg import JointTrajectoryPoint
from std_srvs.srv import SetBool
from dynamixel_interfaces.srv import RebootDxl, GetDataFromDxl

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

ARM_JOINTS = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5']
# limites conservadores (rad) segun docs OMX-F
LIMITS = {
    'joint1': (-4.71, 6.28),
    'joint2': (-2.09, 1.57),
    'joint3': (-2.09, 1.57),
    'joint4': (-1.74, 1.74),
    'joint5': (-4.71, 4.71),
}
HOME = [0.0, -1.57, 1.57, 1.57, 0.0]
INIT = [0.0, 0.0, 0.0, 0.0, 0.0]

app = FastAPI(title='omx-bridge')
node: Node | None = None
arm_client: ActionClient | None = None
grip_client: ActionClient | None = None
torque_client = None
reboot_client = None
getdata_client = None
latest_state: dict = {'names': [], 'position': []}
state_lock = threading.Lock()


class MoveJoints(BaseModel):
    joints: list[float] = Field(min_length=5, max_length=5)
    seconds: float = 4.0


class Gripper(BaseModel):
    open: float = 1.0
    seconds: float = 2.0


class Torque(BaseModel):
    on: bool = True


def validate_joints(q):
    for name, v in zip(ARM_JOINTS, q):
        lo, hi = LIMITS[name]
        if not (lo - 1e-6 <= v <= hi + 1e-6):
            raise HTTPException(400, f'{name}={v} fuera de [{lo},{hi}]')


def _wait(fut, timeout):
    """Espera sin crear otro executor ( el spin global ya corre )."""
    t0 = time.time()
    while not fut.done() and (time.time() - t0) < timeout:
        time.sleep(0.05)
    return fut.done()


def send_arm_goal(q, secs):
    validate_joints(q)
    goal = FollowJointTrajectory.Goal()
    goal.trajectory.joint_names = ARM_JOINTS
    p = JointTrajectoryPoint()
    p.positions = [float(x) for x in q]
    p.time_from_start.sec = int(secs)
    p.time_from_start.nanosec = int((secs % 1) * 1e9)
    goal.trajectory.points = [p]
    fut = arm_client.send_goal_async(goal)
    if not _wait(fut, 10):
        raise HTTPException(504, 'controlador no responde (goal)')
    gh = fut.result()
    if gh is None or not gh.accepted:
        raise HTTPException(409, 'controlador no acepto meta (¿bringup caido?)')
    fr = gh.get_result_async()
    if not _wait(fr, secs + 15):
        raise HTTPException(504, 'sin respuesta del controlador')
    res = fr.result()
    if res is None:
        raise HTTPException(504, 'sin respuesta del controlador')
    return {'status': int(res.status)}


def on_joint(msg: JointState):
    with state_lock:
        latest_state['names'] = list(msg.name)
        latest_state['position'] = list(msg.position)


@app.get('/health')
def health():
    return {'ok': True, 'has_state': bool(latest_state['names'])}


@app.get('/state')
def state():
    with state_lock:
        if not latest_state['names']:
            raise HTTPException(503, 'aun sin /joint_states (¿bringup corriendo?)')
        pos = dict(zip(latest_state['names'], latest_state['position']))
    arm = [pos.get(j) for j in ARM_JOINTS]
    return {'arm': arm, 'gripper': pos.get('gripper_joint_1'), 'all': pos}


@app.post('/move_joints')
def move_joints(m: MoveJoints):
    return send_arm_goal(m.joints, m.seconds)


@app.post('/home')
def home():
    return send_arm_goal(HOME, 5.0)


@app.post('/init')
def init():
    return send_arm_goal(INIT, 5.0)


@app.post('/gripper')
def gripper(g: Gripper):
    if not (0.0 <= g.open <= 1.0):
        raise HTTPException(400, 'open debe ser 0..1')
    goal = GripperCommand.Goal()
    goal.command.position = float(g.open)
    fut = grip_client.send_goal_async(goal)
    if not _wait(fut, 10):
        raise HTTPException(504, 'gripper no responde')
    gh = fut.result()
    if gh is None or not gh.accepted:
        raise HTTPException(409, 'gripper no acepto meta')
    fr = gh.get_result_async()
    if not _wait(fr, g.seconds + 10):
        return {'status': 'timeout-pero-quiza-se-movio-revisa-estado'}
    r = fr.result()
    return {'status': int(r.status) if r else -1}


@app.post('/torque')
def torque(t: Torque):
    req = SetBool.Request(data=bool(t.on))
    fut = torque_client.call_async(req)
    if not _wait(fut, 10):
        raise HTTPException(504, 'torque sin respuesta')
    r = fut.result()
    return {'success': bool(r.success) if r else False, 'msg': r.message if r else 'timeout'}


@app.post('/reboot')
def reboot():
    fut = reboot_client.call_async(RebootDxl.Request())
    if not _wait(fut, 15):
        raise HTTPException(504, 'reboot sin respuesta')
    r = fut.result()
    return {'result': bool(r.result) if r else False}


def main():
    global node, arm_client, grip_client, torque_client, reboot_client, getdata_client
    rclpy.init()
    node = Node('omx_bridge')
    node.create_subscription(JointState, '/joint_states', on_joint, 10)
    arm_client = ActionClient(node, FollowJointTrajectory, '/arm_controller/follow_joint_trajectory')
    grip_client = ActionClient(node, GripperCommand, '/gripper_controller/gripper_cmd')
    torque_client = node.create_client(SetBool, '/dynamixel_hardware_interface/set_dxl_torque')
    reboot_client = node.create_client(RebootDxl, '/dynamixel_hardware_interface/reboot_dxl')
    getdata_client = node.create_client(GetDataFromDxl, '/dynamixel_hardware_interface/get_dxl_data')
    print('esperando servers...', flush=True)
    arm_client.wait_for_server(timeout_sec=15)
    torque_client.wait_for_service(timeout_sec=10)
    reboot_client.wait_for_service(timeout_sec=10)
    print('bridge listo', flush=True)
    t = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    t.start()
    uvicorn.run(app, host='0.0.0.0', port=8000, log_level='info')


if __name__ == '__main__':
    main()
