"""Resuelve agent.ros.bindings (explícitos o inferidos desde interfaces)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .profile import RobotProfile
from .ros_schema import AgentRosSchema, RosInterfaceEntry


@dataclass(frozen=True)
class ActionBinding:
    name: str
    type_name: str = 'control_msgs/action/FollowJointTrajectory'
    joint_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class ServiceBinding:
    name: str
    type_name: str = 'std_srvs/srv/Empty'


@dataclass(frozen=True)
class GripperBinding:
    kind: str  # action | service
    name: str
    type_name: str = 'control_msgs/action/GripperCommand'


@dataclass(frozen=True)
class RosBindings:
    state_topic: str = ''
    state_msg_type: str = 'sensor_msgs/msg/JointState'
    cmd_vel_topic: str = ''
    reset_service: str = ''
    reset_service_type: str = 'std_srvs/srv/Empty'
    trajectory: ActionBinding | None = None
    gripper: GripperBinding | None = None
    torque_service: ServiceBinding | None = None
    joint_state_joint_names: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> RosBindings | None:
        if not data:
            return None
        traj_raw = data.get('trajectory') or data.get('motion')
        trajectory = None
        if traj_raw and isinstance(traj_raw, dict):
            trajectory = ActionBinding(
                name=str(traj_raw.get('name', '')),
                type_name=str(
                    traj_raw.get('type')
                    or traj_raw.get('action_type')
                    or 'control_msgs/action/FollowJointTrajectory'
                ),
                joint_names=tuple(str(x) for x in (traj_raw.get('joint_names') or ())),
            )
        grip_raw = data.get('gripper')
        gripper = None
        if grip_raw and isinstance(grip_raw, dict):
            gripper = GripperBinding(
                kind=str(grip_raw.get('kind', 'action')),
                name=str(grip_raw.get('name', '')),
                type_name=str(
                    grip_raw.get('type')
                    or 'control_msgs/action/GripperCommand'
                ),
            )
        torque_raw = data.get('torque')
        torque = None
        if torque_raw and isinstance(torque_raw, dict):
            torque = ServiceBinding(
                name=str(torque_raw.get('name', '')),
                type_name=str(torque_raw.get('type') or 'std_srvs/srv/SetBool'),
            )
        reset_raw = data.get('reset') or data.get('home_service')
        reset_name = ''
        reset_type = 'std_srvs/srv/Empty'
        if isinstance(reset_raw, dict):
            reset_name = str(reset_raw.get('name', ''))
            reset_type = str(reset_raw.get('type') or reset_type)
        elif isinstance(reset_raw, str):
            reset_name = reset_raw
        return cls(
            state_topic=str(data.get('state_topic') or data.get('joint_state_topic') or ''),
            state_msg_type=str(
                data.get('state_msg_type') or 'sensor_msgs/msg/JointState'
            ),
            cmd_vel_topic=str(data.get('cmd_vel_topic') or ''),
            reset_service=reset_name,
            reset_service_type=reset_type,
            trajectory=trajectory,
            gripper=gripper,
            torque_service=torque,
            joint_state_joint_names=tuple(
                str(x) for x in (data.get('joint_state_joint_names') or ())
            ),
        )


def _first_interface(schema: AgentRosSchema, kind: str) -> RosInterfaceEntry | None:
    for iface in schema.interfaces:
        if iface.kind == kind:
            return iface
    return None


def _service_named(schema: AgentRosSchema, substring: str) -> RosInterfaceEntry | None:
    sub = substring.lower()
    for iface in schema.interfaces:
        if iface.kind == 'service' and sub in iface.name.lower():
            return iface
    return None


def infer_bindings(schema: AgentRosSchema, profile: RobotProfile) -> RosBindings:
    state_sub = _first_interface(schema, 'topic_sub')
    cmd_pub = _first_interface(schema, 'topic_pub')
    reset_svc = _service_named(schema, 'reset') or _first_interface(schema, 'service')

    state_topic = state_sub.name if state_sub else '/joint_states'
    state_msg = state_sub.type_name if state_sub else 'sensor_msgs/msg/JointState'
    if state_sub and 'turtlesim' in state_sub.type_name.lower():
        state_msg = state_sub.type_name

    cmd_vel = ''
    if schema.motion.kind == 'velocity_timed' and cmd_pub:
        cmd_vel = cmd_pub.name

    reset_name = reset_svc.name if reset_svc else ''
    reset_type = reset_svc.type_name if reset_svc else 'std_srvs/srv/Empty'

    trajectory: ActionBinding | None = None
    if schema.motion.kind == 'joint_positions':
        jnames = tuple(profile.joint_names)
        trajectory = ActionBinding(
            name='/arm_controller/follow_joint_trajectory',
            joint_names=jnames,
        )

    gripper: GripperBinding | None = None
    if profile.capabilities.gripper:
        gripper = GripperBinding(
            kind='action',
            name='/gripper_controller/gripper_cmd',
        )

    torque: ServiceBinding | None = None
    if profile.capabilities.torque:
        torque = ServiceBinding(
            name='/dynamixel_hardware_interface/set_dxl_torque',
            type_name='std_srvs/srv/SetBool',
        )

    return RosBindings(
        state_topic=state_topic,
        state_msg_type=state_msg,
        cmd_vel_topic=cmd_vel,
        reset_service=reset_name,
        reset_service_type=reset_type,
        trajectory=trajectory,
        gripper=gripper,
        torque_service=torque,
        joint_state_joint_names=tuple(profile.joint_names),
    )


def resolve_bindings(
    schema: AgentRosSchema,
    profile: RobotProfile,
    raw: dict[str, Any] | None,
) -> RosBindings:
    explicit = RosBindings.from_dict(raw)
    inferred = infer_bindings(schema, profile)
    if explicit is None:
        return inferred

    trajectory = explicit.trajectory or inferred.trajectory
    if trajectory and not trajectory.joint_names:
        trajectory = ActionBinding(
            name=trajectory.name,
            type_name=trajectory.type_name,
            joint_names=inferred.joint_state_joint_names or tuple(profile.joint_names),
        )

    return RosBindings(
        state_topic=explicit.state_topic or inferred.state_topic,
        state_msg_type=explicit.state_msg_type or inferred.state_msg_type,
        cmd_vel_topic=explicit.cmd_vel_topic or inferred.cmd_vel_topic,
        reset_service=explicit.reset_service or inferred.reset_service,
        reset_service_type=explicit.reset_service_type or inferred.reset_service_type,
        trajectory=trajectory,
        gripper=explicit.gripper or inferred.gripper,
        torque_service=explicit.torque_service or inferred.torque_service,
        joint_state_joint_names=(
            explicit.joint_state_joint_names or inferred.joint_state_joint_names
        ),
    )
