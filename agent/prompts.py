"""System prompt generado desde perfil, tools y agent.ros."""
from __future__ import annotations

from .context import get_profile


def _ros_block() -> str:
    p = get_profile()
    schema = p.ros_schema
    if not schema.interfaces:
        return ''
    lines = ['Interfaz ROS (declarada en configs/robots/*.json):']
    for iface in schema.interfaces:
        typ = iface.type_name or iface.kind
        lines.append(f'  - {iface.kind} {iface.name}' + (f' ({typ})' if typ else ''))
    state = schema.state.representation
    motion = schema.motion.kind
    lines.append(f'  state: {state} | motion: {motion}')
    return '\n'.join(lines)


def _tools_block() -> str:
    p = get_profile()
    lines = ['Tools disponibles (generadas por el framework):']
    for spec in p.tool_specs:
        params = ', '.join(x.name for x in spec.parameters) or '(sin parámetros)'
        lines.append(f'  - {spec.name}({params}): {spec.description}')
    return '\n'.join(lines)


def build_system_prompt() -> str:
    p = get_profile()
    header = (
        f'Eres el agente ROS de {p.display_name} (id={p.id}). '
        f'Control directo vía rclpy (mismo proceso ROS 2); tools generadas desde agent.ros.'
    )
    rules = '\n'.join(f'- {r}' for r in p.agent_rules)
    parts = [
        header,
        'Reglas:',
        rules,
        _tools_block(),
    ]
    ros_blk = _ros_block()
    if ros_blk:
        parts.append(ros_blk)
    if p.system_prompt_extra:
        parts.append(p.system_prompt_extra)
    return '\n'.join(parts)
