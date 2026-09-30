"""Tools de introspección ROS 2 (estilo ROSA, solo lectura vía CLI)."""
from __future__ import annotations

import re
import subprocess
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


def _run_ros2(cmd: str, timeout: float = 15.0) -> tuple[bool, str]:
    parts = cmd.split()
    if len(parts) < 2 or parts[0] != 'ros2':
        return False, 'comando inválido (debe empezar con ros2)'
    allowed = {'node', 'topic', 'service', 'param', 'doctor'}
    if parts[1] not in allowed:
        return False, f'subcomando ros2 {parts[1]} no permitido'
    try:
        out = subprocess.check_output(
            cmd, shell=True, stderr=subprocess.STDOUT, timeout=timeout, text=True
        )
        return True, out
    except subprocess.CalledProcessError as e:
        return False, (e.output or str(e))[:500]
    except Exception as e:
        return False, str(e)[:500]


def _filter_lines(text: str, pattern: Optional[str]) -> list[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not pattern:
        return lines
    rx = re.compile(f'.*{pattern}.*')
    return [ln for ln in lines if rx.match(ln)]


class _PatternArgs(BaseModel):
    pattern: Optional[str] = Field(
        default=None, description='filtro regex opcional sobre nombres'
    )


class _TopicEchoArgs(BaseModel):
    topic: str = Field(description='nombre del topic, ej. /joint_states')
    count: int = Field(default=1, ge=1, le=3, description='mensajes a leer (máx 3)')


def ros2_node_list(pattern: Optional[str] = None) -> str:
    ok, out = _run_ros2('ros2 node list')
    if not ok:
        return out
    nodes = _filter_lines(out, pattern)
    return str({'nodes': nodes})


def ros2_topic_list(pattern: Optional[str] = None) -> str:
    ok, out = _run_ros2('ros2 topic list')
    if not ok:
        return out
    topics = _filter_lines(out, pattern)
    return str({'topics': topics})


def ros2_service_list(pattern: Optional[str] = None) -> str:
    ok, out = _run_ros2('ros2 service list')
    if not ok:
        return out
    services = _filter_lines(out, pattern)
    return str({'services': services})


def ros2_topic_echo(topic: str, count: int = 1) -> str:
    if not topic.startswith('/'):
        topic = '/' + topic
    echoes: list[str] = []
    for _ in range(count):
        ok, out = _run_ros2(f'ros2 topic echo {topic} --once', timeout=8.0)
        if not ok:
            return out
        echoes.append(out[:800])
    return str({'topic': topic, 'echoes': echoes})


def build_introspection_tools() -> list[StructuredTool]:
    return [
        StructuredTool.from_function(
            func=ros2_node_list,
            name='ros2_node_list',
            description='Lista nodos ROS 2 activos (solo lectura).',
            args_schema=_PatternArgs,
        ),
        StructuredTool.from_function(
            func=ros2_topic_list,
            name='ros2_topic_list',
            description='Lista topics ROS 2 (solo lectura).',
            args_schema=_PatternArgs,
        ),
        StructuredTool.from_function(
            func=ros2_service_list,
            name='ros2_service_list',
            description='Lista servicios ROS 2 (solo lectura).',
            args_schema=_PatternArgs,
        ),
        StructuredTool.from_function(
            func=ros2_topic_echo,
            name='ros2_topic_echo',
            description='Lee hasta 3 mensajes de un topic (--once).',
            args_schema=_TopicEchoArgs,
        ),
    ]
