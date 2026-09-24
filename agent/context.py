"""Runtime activo: perfil + adapter (se elige vía ROS_AGENT_ROBOT / ROS_AGENT_CONFIG)."""
from __future__ import annotations

from pathlib import Path

from .adapter.factory import load_robot_bundle
from .adapter.http_bridge import HttpBridgeAdapter
from .env_config import env
from .profile import RobotProfile

_PKG_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = _PKG_ROOT.parent
_CONFIGS_DIR = _REPO_ROOT / 'configs' / 'robots'

_profile: RobotProfile | None = None
_adapter: HttpBridgeAdapter | None = None
_config_path: Path | None = None


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


def get_adapter() -> HttpBridgeAdapter:
    _ensure_loaded()
    assert _adapter is not None
    return _adapter


def active_config_path() -> Path | None:
    return _config_path


def reload() -> None:
    global _profile, _adapter, _config_path
    _profile = None
    _adapter = None
    _config_path = None
    from . import graph as graph_mod

    graph_mod.reset_graph()
    from . import tools_lc

    tools_lc.reset_tools_cache()


def _ensure_loaded() -> None:
    global _profile, _adapter, _config_path
    if _profile is not None and _adapter is not None:
        return
    path = resolve_config_path()
    profile, adapter, raw = load_robot_bundle(path)
    bridge_override = env('BRIDGE')
    if bridge_override:
        adapter._config.base_url = bridge_override.rstrip('/')
    _profile = profile
    _adapter = adapter
    _config_path = path


def robot_public_info() -> dict:
    p = get_profile()
    return {
        'id': p.id,
        'display_name': p.display_name,
        'dof': p.dof,
        'tools_fingerprint': p.tools_fingerprint,
        'tool_names': [t.name for t in p.tool_specs],
        'config': str(active_config_path() or ''),
        'bridge': get_adapter()._config.base_url,
    }
