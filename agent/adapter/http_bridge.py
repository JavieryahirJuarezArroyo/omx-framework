"""Adapter HTTP genérico: ROS 2 (u otro middleware) expuesto como REST en el robot/edge."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from ..profile import RobotProfile


@dataclass
class HttpBridgeConfig:
    base_url: str
    paths: dict[str, str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HttpBridgeConfig:
        adapter = data.get('adapter') or data
        paths = dict(adapter.get('paths') or {})
        defaults = {
            'health': '/health',
            'state': '/state',
            'move_joints': '/move_joints',
            'home': '/home',
            'init': '/init',
            'gripper': '/gripper',
            'torque': '/torque',
        }
        for k, v in defaults.items():
            paths.setdefault(k, v)
        base = str(adapter.get('base_url', 'http://localhost:8000')).rstrip('/')
        return cls(base_url=base, paths=paths)


class HttpBridgeAdapter:
    """Cliente REST estándar del framework (sin dependencia de ROS en el host)."""

    def __init__(self, profile: RobotProfile, config: HttpBridgeConfig):
        self.profile = profile
        self._config = config

    def _req(self, method: str, path: str, body: dict | None = None, timeout: float = 30):
        url = self._config.base_url + path
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            url, data=data, method=method, headers={'Content-Type': 'application/json'}
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as f:
                raw = f.read().decode()
                return json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:300]
            raise RuntimeError(f'{path} -> HTTP {e.code}: {detail}') from e

    def get_state(self) -> dict:
        return self._req('GET', self._config.paths['state'], timeout=10)

    def health(self) -> dict:
        return self._req('GET', self._config.paths['health'], timeout=5)

    def move_joints(self, joints: list[float], seconds: float = 4.0) -> dict:
        return self._req(
            'POST',
            self._config.paths['move_joints'],
            {'joints': list(joints), 'seconds': seconds},
            timeout=seconds + 25,
        )

    def home(self) -> dict:
        return self._req('POST', self._config.paths['home'], timeout=30)

    def init(self) -> dict:
        return self._req('POST', self._config.paths['init'], timeout=30)

    def gripper(self, open01: float, seconds: float = 2.0) -> dict:
        return self._req(
            'POST',
            self._config.paths['gripper'],
            {'open': open01, 'seconds': seconds},
            timeout=20,
        )

    def torque(self, on: bool) -> dict:
        return self._req('POST', self._config.paths['torque'], {'on': on}, timeout=10)
