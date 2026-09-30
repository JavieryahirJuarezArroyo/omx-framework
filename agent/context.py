"""Runtime activo: perfil + adapter ROS 2 (ROS_AGENT_ROBOT / ROS_AGENT_CONFIG)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .adapter.factory import RobotAdapter, create_adapter, load_profile_bundle
from .env_config import env
from .profile import RobotProfile

_PKG_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _PKG_ROOT.parent
_CONFIGS_DIR = _REPO_ROOT / 'configs' / 'robots'

_profile: RobotProfile | None = None
_adapter: RobotAdapter | None = None
_config_path: Path | None = None
_raw_config: dict[str, Any] | None = None


def configs_dir() -> Path:
    return _CONFIGS_DIR


def resolve_config_path() -> Path:
    explicit = env('CONFIG')
    if explicit:
        p = Path(explicit)
        if not p.is_absolute():
            p = _REPO_ROOT / p
        return p
    robot_id = env('ROBOT', 'open_manipulator_omx_f')
    candidate = _CONFIGS_DIR / f'{robot_id}.json'
    if candidate.is_file():
        return candidate
    legacy = _CONFIGS_DIR / 'default.json'
    if legacy.is_file():
        return legacy
    raise FileNotFoundError(
        f'No hay config para robot "{robot_id}". '
        f'Crea {_CONFIGS_DIR}/{robot_id}.json o define ROS_AGENT_CONFIG.'
    )


def get_profile() -> RobotProfile:
    _ensure_loaded()
    assert _profile is not None
    return _profile


def get_adapter() -> RobotAdapter:
    return ensure_ros_adapter()


def _create_adapter_if_needed() -> None:
    global _adapter
    if _adapter is not None:
        return
    assert _profile is not None and _raw_config is not None
    _adapter = create_adapter(_profile, _raw_config)


def active_config_path() -> Path | None:
    return _config_path


def reload() -> None:
    global _profile, _adapter, _config_path, _raw_config
    _profile = None
    _adapter = None
    _config_path = None
    _raw_config = None
    from . import graph as graph_mod

    graph_mod.reset_graph()
    from . import tools_lc

    tools_lc.reset_tools_cache()


def _ensure_loaded() -> None:
    global _profile, _adapter, _config_path, _raw_config
    if _profile is not None:
        return
    path = resolve_config_path()
    profile, raw = load_profile_bundle(path)
    _profile = profile
    _config_path = path
    _raw_config = raw


def ensure_ros_adapter() -> RobotAdapter:
    """Inicializa rclpy y el adapter (llamar antes de mover/leer estado)."""
    _ensure_loaded()
    _create_adapter_if_needed()
    assert _adapter is not None
    return _adapter


def adapter_public_info() -> dict:
    raw = _raw_config or {}
    adapter_block = raw.get('adapter') or {}
    return {
        'type': str(adapter_block.get('type', 'ros2')),
        'node_name': str(adapter_block.get('node_name', 'ros_agent_bridge')),
    }


def robot_public_info() -> dict:
    p = get_profile()
    info = adapter_public_info()
    return {
        'id': p.id,
        'display_name': p.display_name,
        'dof': p.dof,
        'tools_fingerprint': p.tools_fingerprint,
        'tool_names': [t.name for t in p.tool_specs],
        'config': str(active_config_path() or ''),
        'adapter': info['type'],
        'ros_node': info['node_name'],
    }
