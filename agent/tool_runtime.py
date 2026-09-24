"""Ejecuta ToolSpec contra el bridge HTTP y construye StructuredTool."""
from __future__ import annotations

import json
from typing import Any, Callable

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

from . import safety, tools
from .context import get_profile
from .tool_spec import BridgeAction, ParamSpec, ToolSpec


def _read_positions() -> list[float]:
    return tools.read_arm_positions()


def _resolve_joints(template: Any, kwargs: dict[str, Any], dof: int) -> list[float]:
    if template == '$joints':
        joints = kwargs.get('joints')
        if joints is None:
            raise ValueError('falta parámetro joints')
        return [float(x) for x in joints]
    if isinstance(template, list):
        out: list[float] = []
        for item in template:
            if isinstance(item, str) and item.startswith('$'):
                key = item[1:]
                if key not in kwargs:
                    raise ValueError(f'falta parámetro {key}')
                out.append(float(kwargs[key]))
            else:
                out.append(float(item))
        return out
    raise ValueError(f'joints_template inválido: {template}')


def _execute_bridge(action: BridgeAction, tool_name: str, kwargs: dict[str, Any]) -> str:
    p = get_profile()
    op = action.op

    if op == 'read_state':
        try:
            st = tools.get_state()
            arm = [round(x, 3) for x in tools.read_arm_positions(st)]
            if action.present == 'pose_2d':
                payload = {
                    'x': arm[0],
                    'y': arm[1],
                    'theta': arm[2],
                    'labels': p.joint_names,
                }
            elif action.present == 'joints':
                payload = {'arm': arm, 'joint_names': p.joint_names}
                if action.include_gripper and p.capabilities.gripper:
                    payload['gripper'] = round(tools.read_gripper(st), 3)
            else:
                payload = st
            return json.dumps(payload, ensure_ascii=False)
        except Exception as e:
            return f'Error leyendo estado: {e}'

    if op == 'move_joints':
        seconds = float(kwargs.get(action.seconds_param, 2.0))
        try:
            joints = _resolve_joints(action.joints_template, kwargs, p.dof)
        except ValueError as e:
            return f'Error: {e}'
        if action.joints_template == '$joints' and len(joints) != p.dof:
            return f'Error: se necesitan {p.dof} joints, recibí {len(joints)}.'
        try:
            current = _read_positions()
        except Exception as e:
            return f'No pude leer estado antes de mover: {e}'
        if action.safety_max_step:
            step_err = safety.check_max_step(current, joints)
            if step_err:
                return step_err
        clamped, noted = (
            safety.clamp_joints(joints) if action.safety_clamp else (joints, [])
        )
        notes = f' Nota clamp: {"; ".join(noted)}.' if noted else ''
        try:
            tools.move_joints(clamped, seconds)
        except Exception as e:
            return f'{tool_name} falló: {e}'
        try:
            after = _read_positions()
        except Exception as e:
            return f'Movimiento enviado{notes} pero no pude leer estado final: {e}'
        if action.verify == 'velocity':
            arm_r = [round(x, 3) for x in after]
            approx = round(clamped[0] * seconds, 3) if clamped else 0
            return (
                f'{tool_name} ok cmd={clamped[:2]} {seconds}s (≈{approx} m recto). '
                f'Pose/estado={arm_r}{notes}'
            )
        if action.verify == 'position':
            msg = safety.format_move_verification(tool_name, clamped, after)
            return msg + notes
        return f'{tool_name} ok{notes}'

    if op == 'home':
        try:
            tools.home()
        except Exception as e:
            return f'{tool_name} falló: {e}'
        if action.verify == 'none':
            try:
                after = _read_positions()
                return f'{tool_name} ok. estado={ [round(x, 3) for x in after] }'
            except Exception as e:
                return f'{tool_name} enviado; no pude leer estado: {e}'
        target = (
            safety.home_pose()
            if action.verify_target == 'home_pose'
            else safety.init_pose()
        )
        try:
            after = _read_positions()
        except Exception as e:
            return f'{tool_name} enviado pero no pude leer estado: {e}'
        return safety.format_move_verification(tool_name, target, after)

    if op == 'init':
        try:
            tools.init()
        except Exception as e:
            return f'{tool_name} falló: {e}'
        target = safety.init_pose()
        try:
            after = _read_positions()
        except Exception as e:
            return f'{tool_name} enviado pero no pude leer estado: {e}'
        return safety.format_move_verification(tool_name, target, after)

    if op == 'gripper':
        try:
            open_v = max(0.0, min(1.0, float(kwargs[action.gripper_param])))
            res = tools.gripper(open_v)
            st = tools.get_state()
            grip = round(tools.read_gripper(st), 3)
            return f'gripper ok open={open_v}. estado={grip}. {res}'
        except Exception as e:
            return f'{tool_name} falló: {e}'

    if op == 'torque':
        try:
            on = bool(kwargs[action.torque_param])
            res = tools.torque(on)
            return f'torque {"ON" if on else "OFF"} ok: {res}'
        except Exception as e:
            return f'{tool_name} falló: {e}'

    return f'op bridge desconocida: {op}'


def _pydantic_type(param: ParamSpec) -> Any:
    if param.type == 'boolean':
        return bool
    if param.type == 'integer':
        return int
    if param.type == 'array':
        return list[float]
    return float


def _args_model(spec: ToolSpec) -> type[BaseModel]:
    if not spec.parameters:
        return create_model(f'{spec.name}_Args')
    fields: dict[str, Any] = {}
    for p in spec.parameters:
        py_t = _pydantic_type(p)
        if p.required:
            fields[p.name] = (py_t, Field(description=p.description))
        else:
            fields[p.name] = (
                py_t,
                Field(default=p.default, description=p.description),
            )
    return create_model(f'{spec.name}_Args', **fields)


def _make_callable(spec: ToolSpec) -> Callable:
    action = spec.bridge
    if action is None:
        raise ValueError(f'tool {spec.name} sin bridge')

    if not spec.parameters:

        def fn() -> str:
            return _execute_bridge(action, spec.name, {})

        fn.__name__ = spec.name
        fn.__doc__ = spec.description
        return fn

    def fn(**kwargs: Any) -> str:
        return _execute_bridge(action, spec.name, kwargs)

    fn.__name__ = spec.name
    fn.__doc__ = spec.description
    return fn


def build_structured_tool(spec: ToolSpec) -> StructuredTool:
    fn = _make_callable(spec)
    schema = _args_model(spec)
    return StructuredTool.from_function(
        func=fn,
        name=spec.name,
        description=spec.description,
        args_schema=schema if spec.parameters else None,
    )


def build_all_tools(specs: tuple[ToolSpec, ...]) -> list[StructuredTool]:
    return [build_structured_tool(s) for s in specs]
