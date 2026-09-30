"""Especificación declarativa de tools (JSON → runtime LangChain)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class ParamSpec:
    name: str
    type: Literal['number', 'integer', 'boolean', 'array'] = 'number'
    description: str = ''
    required: bool = True
    default: Any = None
    array_item_type: Literal['number'] = 'number'

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParamSpec:
        return cls(
            name=str(data['name']),
            type=str(data.get('type', 'number')),
            description=str(data.get('description', '')),
            required=bool(data.get('required', True)),
            default=data.get('default'),
            array_item_type=str(data.get('array_item_type', 'number')),
        )


@dataclass(frozen=True)
class RosAction:
    op: Literal['read_state', 'move_joints', 'home', 'init', 'gripper', 'torque']
    present: Literal['joints', 'pose_2d', 'raw'] | None = None
    include_gripper: bool = False
    joints_template: Any = None
    seconds_param: str = 'seconds'
    safety_max_step: bool = False
    safety_clamp: bool = True
    verify: Literal['position', 'velocity', 'none'] = 'position'
    verify_target: Literal['home_pose', 'init_pose'] | None = None
    gripper_param: str = 'open'
    torque_param: str = 'on'

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RosAction:
        return cls(
            op=str(data['op']),
            present=data.get('present'),
            include_gripper=bool(data.get('include_gripper', False)),
            joints_template=data.get('joints'),
            seconds_param=str(data.get('seconds_param', 'seconds')),
            safety_max_step=bool(data.get('safety_max_step', False)),
            safety_clamp=bool(data.get('safety_clamp', True)),
            verify=str(data.get('verify', 'position')),
            verify_target=data.get('verify_target'),
            gripper_param=str(data.get('gripper_param', 'open')),
            torque_param=str(data.get('torque_param', 'on')),
        )


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: tuple[ParamSpec, ...] = ()
    bridge: RosAction | None = None
    ros_refs: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolSpec:
        params = tuple(ParamSpec.from_dict(p) for p in (data.get('parameters') or []))
        bridge_raw = data.get('bridge')
        bridge = RosAction.from_dict(bridge_raw) if bridge_raw else None
        ros_refs = tuple(str(x) for x in (data.get('ros_refs') or []))
        return cls(
            name=str(data['name']),
            description=str(data.get('description', '')),
            parameters=params,
            bridge=bridge,
            ros_refs=ros_refs,
        )

    def fingerprint(self) -> str:
        return json.dumps(
            {
                'name': self.name,
                'description': self.description,
                'parameters': [p.name for p in self.parameters],
                'bridge': self.bridge.op if self.bridge else None,
            },
            sort_keys=True,
        )


BridgeAction = RosAction
