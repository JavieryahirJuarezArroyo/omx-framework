"""Adapter ROS 2 (rclpy): el agente es nodo en el mismo proceso que el robot/sim."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

from ..profile import RobotProfile
from ..ros_bindings import RosBindings

_SPIN_LOCK = threading.Lock()
_RCLPY_INITIALIZED = False
_EXECUTOR = None


def _ensure_rclpy() -> None:
    global _RCLPY_INITIALIZED
    if _RCLPY_INITIALIZED:
        return
    with _SPIN_LOCK:
        if _RCLPY_INITIALIZED:
            return
        import rclpy

        if not rclpy.ok():
            rclpy.init()
        _RCLPY_INITIALIZED = True


def _wait_future(fut, timeout: float) -> bool:
    t0 = time.time()
    while not fut.done() and (time.time() - t0) < timeout:
        time.sleep(0.05)
    return fut.done()


@dataclass
class Ros2AdapterConfig:
    node_name: str = 'ros_agent_bridge'

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Ros2AdapterConfig:
        adapter = data.get('adapter') or {}
        return cls(node_name=str(adapter.get('node_name', 'ros_agent_bridge')))


class Ros2Adapter:
    """Publica/suscribe/ejecuta actions según bindings del perfil."""

    def __init__(self, profile: RobotProfile, config: Ros2AdapterConfig):
        self.profile = profile
        self._config = config
        self._bindings: RosBindings = profile.ros_schema.bindings_for(profile)
        self._node = None
        self._pose_lock = threading.Lock()
        self._joint_lock = threading.Lock()
        self._latest_pose = {'x': 0.0, 'y': 0.0, 'theta': 0.0, 'ready': False}
        self._latest_joints: dict = {'names': [], 'position': []}
        self._cmd_pub = None
        self._reset_client = None
        self._arm_client = None
        self._grip_client = None
        self._torque_client = None
        self._setup_node()

    def _setup_node(self) -> None:
        _ensure_rclpy()
        import rclpy
        from rclpy.node import Node

        self._node = Node(self._config.node_name)
        b = self._bindings
        state_type = (b.state_msg_type or '').lower()

        if 'turtlesim' in state_type and 'pose' in state_type:
            from turtlesim.msg import Pose

            self._node.create_subscription(
                Pose, b.state_topic, self._on_pose, 10
            )
        else:
            from sensor_msgs.msg import JointState

            self._node.create_subscription(
                JointState, b.state_topic or '/joint_states', self._on_joint, 10
            )

        if b.cmd_vel_topic:
            from geometry_msgs.msg import Twist

            self._cmd_pub = self._node.create_publisher(
                Twist, b.cmd_vel_topic, 10
            )

        if b.reset_service:
            from std_srvs.srv import Empty

            self._reset_client = self._node.create_client(Empty, b.reset_service)

        if b.trajectory and b.trajectory.name:
            from control_msgs.action import FollowJointTrajectory
            from rclpy.action import ActionClient

            self._arm_client = ActionClient(
                self._node,
                FollowJointTrajectory,
                b.trajectory.name,
            )

        if b.gripper and b.gripper.name:
            from control_msgs.action import GripperCommand
            from rclpy.action import ActionClient

            self._grip_client = ActionClient(
                self._node, GripperCommand, b.gripper.name
            )

        if b.torque_service and b.torque_service.name:
            from std_srvs.srv import SetBool

            self._torque_client = self._node.create_client(
                SetBool, b.torque_service.name
            )

        self._start_spin()

    def _start_spin(self) -> None:
        global _EXECUTOR
        from rclpy.executors import MultiThreadedExecutor

        with _SPIN_LOCK:
            if _EXECUTOR is None:
                _EXECUTOR = MultiThreadedExecutor()
                threading.Thread(target=_EXECUTOR.spin, daemon=True).start()
            _EXECUTOR.add_node(self._node)

    def _on_pose(self, msg) -> None:
        with self._pose_lock:
            self._latest_pose['x'] = float(msg.x)
            self._latest_pose['y'] = float(msg.y)
            self._latest_pose['theta'] = float(msg.theta)
            self._latest_pose['ready'] = True

    def _on_joint(self, msg) -> None:
        with self._joint_lock:
            self._latest_joints['names'] = list(msg.name)
            self._latest_joints['position'] = list(msg.position)

    def _arm_vector(self) -> list[float]:
        b = self._bindings
        p = self.profile
        if p.ros_schema.state.representation == 'pose_2d':
            with self._pose_lock:
                if not self._latest_pose['ready']:
                    raise RuntimeError(
                        f'sin datos en {b.state_topic} (¿simulación/nodo corriendo?)'
                    )
                return [
                    self._latest_pose['x'],
                    self._latest_pose['y'],
                    self._latest_pose['theta'],
                ]
        with self._joint_lock:
            if not self._latest_joints['names']:
                raise RuntimeError(
                    f'sin {b.state_topic} (¿bringup corriendo?)'
                )
            pos = dict(
                zip(self._latest_joints['names'], self._latest_joints['position'])
            )
        names = b.joint_state_joint_names or tuple(p.joint_names)
        arm = [float(pos.get(j, 0.0)) for j in names]
        return arm

    def health(self) -> dict:
        try:
            self._arm_vector()
            return {'ok': True}
        except RuntimeError as e:
            return {'ok': False, 'error': str(e)}

    def get_state(self) -> dict:
        arm = self._arm_vector()
        out: dict[str, Any] = {'arm': arm}
        if self.profile.capabilities.gripper:
            with self._joint_lock:
                pos = dict(
                    zip(
                        self._latest_joints.get('names', []),
                        self._latest_joints.get('position', []),
                    )
                )
            g = pos.get('gripper_joint_1')
            if g is not None:
                out['gripper'] = float(g)
        return out

    def move_joints(self, joints: list[float], seconds: float = 4.0) -> dict:
        if self._cmd_pub is not None:
            return self._move_velocity(joints, seconds)
        if self._arm_client is not None:
            return self._move_trajectory(joints, seconds)
        raise RuntimeError('sin cmd_vel ni action de trayectoria en bindings')

    def _move_velocity(self, joints: list[float], seconds: float) -> dict:
        from geometry_msgs.msg import Twist

        lin = float(joints[0]) if joints else 0.0
        ang = float(joints[1]) if len(joints) > 1 else 0.0
        twist = Twist()
        twist.linear.x = lin
        twist.angular.z = ang
        deadline = time.time() + max(0.1, seconds)
        rate_hz = 10.0
        while time.time() < deadline:
            self._cmd_pub.publish(twist)
            time.sleep(1.0 / rate_hz)
        stop = Twist()
        self._cmd_pub.publish(stop)
        return {'ok': True, 'linear_x': lin, 'angular_z': ang, 'seconds': seconds}

    def _move_trajectory(self, joints: list[float], seconds: float) -> dict:
        from control_msgs.action import FollowJointTrajectory
        from trajectory_msgs.msg import JointTrajectoryPoint

        b = self._bindings
        assert b.trajectory is not None
        jnames = list(b.trajectory.joint_names or self.profile.joint_names)
        if len(joints) != len(jnames):
            raise ValueError(f'se esperaban {len(jnames)} joints, recibí {len(joints)}')

        if not self._arm_client.wait_for_server(timeout_sec=15.0):
            raise RuntimeError(f'action {b.trajectory.name} no disponible')

        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = jnames
        pt = JointTrajectoryPoint()
        pt.positions = [float(x) for x in joints]
        pt.time_from_start.sec = int(seconds)
        pt.time_from_start.nanosec = int((seconds % 1) * 1e9)
        goal.trajectory.points = [pt]

        fut = self._arm_client.send_goal_async(goal)
        if not _wait_future(fut, 10):
            raise RuntimeError('controlador no respondió (goal)')
        gh = fut.result()
        if gh is None or not gh.accepted:
            raise RuntimeError('controlador no aceptó meta')
        fr = gh.get_result_async()
        if not _wait_future(fr, seconds + 15):
            raise RuntimeError('sin respuesta del controlador')
        res = fr.result()
        status = int(res.status) if res else -1
        return {'status': status}

    def home(self) -> dict:
        if self._reset_client is not None:
            from std_srvs.srv import Empty

            if not self._reset_client.wait_for_service(timeout_sec=5.0):
                raise RuntimeError('servicio reset no disponible')
            fut = self._reset_client.call_async(Empty.Request())
            if not _wait_future(fut, 5.0):
                raise RuntimeError('timeout reset')
            time.sleep(0.3)
            return {'ok': True, 'arm': self._arm_vector()}
        return self._move_trajectory(list(self.profile.home_pose), 5.0)

    def init(self) -> dict:
        if self.profile.ros_schema.state.representation == 'pose_2d':
            return self.home()
        return self._move_trajectory(list(self.profile.init_pose), 5.0)

    def gripper(self, open01: float, seconds: float = 2.0) -> dict:
        if self._grip_client is None:
            raise RuntimeError('gripper no configurado en bindings')
        from control_msgs.action import GripperCommand

        open01 = max(0.0, min(1.0, float(open01)))
        if not self._grip_client.wait_for_server(timeout_sec=10.0):
            raise RuntimeError('gripper action no disponible')
        goal = GripperCommand.Goal()
        goal.command.position = open01
        fut = self._grip_client.send_goal_async(goal)
        if not _wait_future(fut, 10):
            raise RuntimeError('gripper no respondió')
        gh = fut.result()
        if gh is None or not gh.accepted:
            raise RuntimeError('gripper no aceptó meta')
        fr = gh.get_result_async()
        if not _wait_future(fr, seconds + 10):
            return {'status': 'timeout'}
        r = fr.result()
        return {'status': int(r.status) if r else -1}

    def torque(self, on: bool) -> dict:
        if self._torque_client is None:
            raise RuntimeError('torque no configurado en bindings')
        from std_srvs.srv import SetBool

        if not self._torque_client.wait_for_service(timeout_sec=10.0):
            raise RuntimeError('servicio torque no disponible')
        req = SetBool.Request(data=bool(on))
        fut = self._torque_client.call_async(req)
        if not _wait_future(fut, 10):
            raise RuntimeError('torque sin respuesta')
        r = fut.result()
        return {
            'success': bool(r.success) if r else False,
            'msg': r.message if r else 'timeout',
        }
