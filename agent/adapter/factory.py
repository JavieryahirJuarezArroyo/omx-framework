"""Fabrica de adapters según el bloque adapter del JSON de robot."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from ..profile import RobotProfile, load_profile_path
from .ros2_adapter import Ros2Adapter, Ros2AdapterConfig


@runtime_checkable
class RobotAdapter(Protocol):
    profile: RobotProfile

    def get_state(self) -> dict: ...

    def health(self) -> dict: ...

    def move_joints(self, joints: list[float], seconds: float = 4.0) -> dict: ...

    def home(self) -> dict: ...

    def init(self) -> dict: ...

    def gripper(self, open01: float, seconds: float = 2.0) -> dict: ...

    def torque(self, on: bool) -> dict: ...


def create_adapter(profile: RobotProfile, raw_config: dict[str, Any]) -> RobotAdapter:
    adapter_block = raw_config.get('adapter') or {}
    kind = str(adapter_block.get('type', 'ros2')).lower()
    if kind in ('ros2', 'ros', 'rclpy'):
        return Ros2Adapter(profile, Ros2AdapterConfig.from_dict(raw_config))
    raise ValueError(
        f'Adapter type "{kind}" no soportado. Usa adapter.type: ros2 en el JSON del robot.'
    )


def load_profile_bundle(path: Path) -> tuple[RobotProfile, dict[str, Any]]:
    with path.open(encoding='utf-8') as f:
        raw = json.load(f)
    profile = RobotProfile.from_dict(raw)
    return profile, raw


def load_robot_bundle(path: Path) -> tuple[RobotProfile, RobotAdapter, dict[str, Any]]:
    profile, raw = load_profile_bundle(path)
    adapter = create_adapter(profile, raw)
    return profile, adapter, raw
