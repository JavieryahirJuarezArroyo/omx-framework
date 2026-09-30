"""Perfil de robot cargado desde JSON (agnóstico al hardware concreto)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .ros_schema import AgentRosSchema, RosMotionSchema, RosStateSchema
from .tool_spec import ToolSpec


@dataclass(frozen=True)
class Capabilities:
    gripper: bool = False
    torque: bool = False
    home: bool = True
    init: bool = True


def _empty_ros_schema() -> AgentRosSchema:
    return AgentRosSchema(interfaces=(), state=RosStateSchema(), motion=RosMotionSchema())


@dataclass(frozen=True)
class RobotProfile:
    id: str
    display_name: str
    dof: int
    joint_names: list[str]
    limits: dict[str, tuple[float, float]]
    home_pose: list[float]
    init_pose: list[float]
    capabilities: Capabilities
    known_joint_hints: dict[int, str] = field(default_factory=dict)
    system_prompt_extra: str = ''
    state_arm_key: str = 'arm'
    state_gripper_key: str = 'gripper'
    ros_schema: AgentRosSchema = field(default_factory=_empty_ros_schema)
    tool_specs: tuple[ToolSpec, ...] = ()
    agent_rules: tuple[str, ...] = ()
    tools_fingerprint: str = ''
    introspection: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RobotProfile:
        from .tool_codegen import default_agent_rules, resolve_tool_specs

        robot = data.get('robot') or data
        caps_raw = data.get('capabilities') or robot.get('capabilities') or {}
        limits_raw = robot['limits']
        limits = {k: (float(v[0]), float(v[1])) for k, v in limits_raw.items()}
        hints_raw = robot.get('known_joint_hints') or {}
        hints = {int(k): str(v) for k, v in hints_raw.items()}
        joint_names = list(robot['joint_names'])
        dof = int(robot.get('dof', len(joint_names)))
        if dof != len(joint_names):
            raise ValueError(f'dof={dof} no coincide con joint_names ({len(joint_names)})')
        home = list(robot['home_pose'])
        init = list(robot.get('init_pose', [0.0] * dof))
        if len(home) != dof or len(init) != dof:
            raise ValueError('home_pose/init_pose deben tener longitud dof')
        agent_raw = data.get('agent') or {}
        ros_schema = AgentRosSchema.from_agent_ros(agent_raw.get('ros'))
        caps = Capabilities(
            gripper=bool(caps_raw.get('gripper', False)),
            torque=bool(caps_raw.get('torque', False)),
            home=bool(caps_raw.get('home', True)),
            init=bool(caps_raw.get('init', True)),
        )
        profile_stub = cls(
            id=str(robot.get('id', 'robot')),
            display_name=str(robot.get('display_name', robot.get('id', 'robot'))),
            dof=dof,
            joint_names=joint_names,
            limits=limits,
            home_pose=home,
            init_pose=init,
            capabilities=caps,
            known_joint_hints=hints,
            system_prompt_extra=str(agent_raw.get('system_prompt_extra', '')).strip(),
            state_arm_key=str(robot.get('state_arm_key', 'arm')),
            state_gripper_key=str(robot.get('state_gripper_key', 'gripper')),
            ros_schema=ros_schema,
        )
        tool_specs = resolve_tool_specs(
            profile_stub, ros_schema, agent_raw.get('tools', 'auto')
        )
        behavior = agent_raw.get('behavior') or {}
        rules_raw = behavior.get('rules')
        agent_rules = (
            tuple(str(r) for r in rules_raw)
            if rules_raw
            else default_agent_rules(ros_schema)
        )
        fp_src = '|'.join(t.fingerprint() for t in tool_specs)
        tools_fp = hashlib.sha256(fp_src.encode()).hexdigest()[:16]
        introspection = bool(agent_raw.get('introspection', False))
        return cls(
            id=profile_stub.id,
            display_name=profile_stub.display_name,
            dof=dof,
            joint_names=joint_names,
            limits=limits,
            home_pose=home,
            init_pose=init,
            capabilities=caps,
            known_joint_hints=hints,
            system_prompt_extra=profile_stub.system_prompt_extra,
            state_arm_key=profile_stub.state_arm_key,
            state_gripper_key=profile_stub.state_gripper_key,
            ros_schema=ros_schema,
            tool_specs=tool_specs,
            agent_rules=agent_rules,
            tools_fingerprint=tools_fp,
            introspection=introspection,
        )


def load_profile_path(path: Path) -> RobotProfile:
    with path.open(encoding='utf-8') as f:
        data = json.load(f)
    return RobotProfile.from_dict(data)
