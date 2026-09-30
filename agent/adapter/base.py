"""Contrato de conexión al robot (ROS 2 vía rclpy)."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..profile import RobotProfile


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
