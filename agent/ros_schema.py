"""Modelo agent.ros del perfil (interfaces + state + motion)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class RosInterfaceEntry:
    kind: str
    name: str
    type_name: str = ''

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RosInterfaceEntry:
        kind = str(data.get('kind', 'topic_sub'))
        type_name = str(
            data.get('msg_type') or data.get('srv_type') or data.get('type') or ''
        )
        return cls(kind=kind, name=str(data['name']), type_name=type_name)


@dataclass(frozen=True)
class RosStateSchema:
    representation: Literal['joints', 'pose_2d'] = 'joints'

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> RosStateSchema:
        if not data:
            return cls()
        return cls(representation=str(data.get('representation', 'joints')))


@dataclass(frozen=True)
class MotionInput:
    name: str
    unit: str = ''
    bridge_index: int = 0
    default: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MotionInput:
        return cls(
            name=str(data['name']),
            unit=str(data.get('unit', '')),
            bridge_index=int(data.get('bridge_index', 0)),
            default=data.get('default'),
        )


@dataclass(frozen=True)
class RosMotionSchema:
    kind: Literal['joint_positions', 'velocity_timed'] = 'joint_positions'
    duration_param: str = 'seconds'
    inputs: tuple[MotionInput, ...] = ()
    verify: Literal['position', 'velocity', 'none', ''] = ''

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> RosMotionSchema:
        if not data:
            return cls()
        inputs = tuple(MotionInput.from_dict(i) for i in (data.get('inputs') or []))
        return cls(
            kind=str(data.get('kind', 'joint_positions')),
            duration_param=str(data.get('duration_param', 'seconds')),
            inputs=inputs,
            verify=str(data.get('verify', '')),
        )

    def resolved_verify(self) -> Literal['position', 'velocity', 'none']:
        if self.verify in ('position', 'velocity', 'none'):
            return self.verify
        if self.kind == 'velocity_timed':
            return 'velocity'
        return 'position'


@dataclass(frozen=True)
class AgentRosSchema:
    interfaces: tuple[RosInterfaceEntry, ...]
    state: RosStateSchema
    motion: RosMotionSchema

    @classmethod
    def from_agent_ros(cls, ros_raw: dict[str, Any] | None) -> AgentRosSchema:
        if not ros_raw:
            return cls(interfaces=(), state=RosStateSchema(), motion=RosMotionSchema())
        interfaces: list[RosInterfaceEntry] = []
        if ros_raw.get('interfaces'):
            for item in ros_raw['interfaces']:
                interfaces.append(RosInterfaceEntry.from_dict(item))
        else:
            for name in ros_raw.get('subscribe') or []:
                interfaces.append(RosInterfaceEntry('topic_sub', str(name), ''))
            for name in ros_raw.get('publish') or []:
                interfaces.append(RosInterfaceEntry('topic_pub', str(name), ''))
            for name in ros_raw.get('services') or []:
                interfaces.append(RosInterfaceEntry('service', str(name), ''))
        return cls(
            interfaces=tuple(interfaces),
            state=RosStateSchema.from_dict(ros_raw.get('state')),
            motion=RosMotionSchema.from_dict(ros_raw.get('motion')),
        )

    def interface_names_by_kind(self, kind: str) -> tuple[str, ...]:
        return tuple(i.name for i in self.interfaces if i.kind == kind)
