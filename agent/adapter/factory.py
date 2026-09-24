"""Fabrica de adapters según el bloque adapter del JSON de robot."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..profile import RobotProfile, load_profile_path
from .http_bridge import HttpBridgeAdapter, HttpBridgeConfig


def create_adapter(profile: RobotProfile, raw_config: dict[str, Any]) -> HttpBridgeAdapter:
    adapter_block = raw_config.get('adapter') or {}
    kind = str(adapter_block.get('type', 'http')).lower()
    if kind in ('http', 'http_bridge'):
        return HttpBridgeAdapter(profile, HttpBridgeConfig.from_dict(raw_config))
    raise ValueError(
        f'Adapter type "{kind}" no soportado aún. Usa type: http y un bridge REST sobre ROS.'
    )


def load_robot_bundle(path: Path) -> tuple[RobotProfile, HttpBridgeAdapter, dict[str, Any]]:
    with path.open(encoding='utf-8') as f:
        raw = json.load(f)
    profile = RobotProfile.from_dict(raw)
    adapter = create_adapter(profile, raw)
    return profile, adapter, raw
