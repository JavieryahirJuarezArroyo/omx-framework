"""Tools LangChain generadas dinámicamente desde el perfil (agent.ros + codegen)."""
from __future__ import annotations

from langchain_core.tools import StructuredTool

from .context import get_adapter, get_profile
from .tool_runtime import build_all_tools

_tools_cache: list[StructuredTool] | None = None
_tools_cache_key: str | None = None


def reset_tools_cache() -> None:
    global _tools_cache, _tools_cache_key
    _tools_cache = None
    _tools_cache_key = None


def get_agent_tools() -> list[StructuredTool]:
    global _tools_cache, _tools_cache_key
    p = get_profile()
    key = f'{p.id}:{p.tools_fingerprint}'
    if _tools_cache is not None and _tools_cache_key == key:
        return _tools_cache
    if not p.tool_specs:
        raise ValueError(
            f'Robot {p.id}: sin tools. Define agent.ros y agent.tools="auto" en el JSON.'
        )
    built = build_all_tools(p.tool_specs)
    if p.introspection:
        from .tools_ros_cli import build_introspection_tools

        built = built + build_introspection_tools()
    _tools_cache = built
    _tools_cache_key = key
    return _tools_cache
