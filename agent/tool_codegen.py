"""Genera ToolSpec[] desde agent.ros + capabilities (sin presets por robot)."""
from __future__ import annotations

from .profile import Capabilities, RobotProfile
from .ros_schema import AgentRosSchema, MotionInput, RosMotionSchema
from .tool_spec import BridgeAction, ParamSpec, ToolSpec


def _default_velocity_inputs() -> tuple[MotionInput, ...]:
    return (
        MotionInput('linear_x', 'm/s', 0),
        MotionInput('angular_z', 'rad/s', 1, default=0.0),
    )


def _motion_inputs(motion: RosMotionSchema):
    if motion.inputs:
        return motion.inputs
    if motion.kind == 'velocity_timed':
        return _default_velocity_inputs()
    return ()


def _ros_ref_names(schema: AgentRosSchema, *kinds: str) -> tuple[str, ...]:
    out: list[str] = []
    for k in kinds:
        out.extend(schema.interface_names_by_kind(k))
    return tuple(out)


def _read_tool(schema: AgentRosSchema, profile: RobotProfile) -> ToolSpec:
    present = schema.state.representation
    if present == 'pose_2d':
        name = 'get_pose'
        desc = (
            f'Lee posición 2D de {profile.display_name} '
            f'({", ".join(profile.joint_names)}). Unidades según perfil ROS.'
        )
    else:
        name = 'get_robot_state'
        desc = (
            f'Lee articulaciones de {profile.display_name} '
            f'({profile.dof} DOF: {", ".join(profile.joint_names)}), en radianes.'
        )
    refs = _ros_ref_names(schema, 'topic_sub')
    return ToolSpec(
        name=name,
        description=desc,
        parameters=(),
        bridge=BridgeAction(
            op='read_state',
            present=present,
            include_gripper=profile.capabilities.gripper,
        ),
        ros_refs=refs,
    )


def _motion_tool(schema: AgentRosSchema, profile: RobotProfile) -> ToolSpec:
    motion = schema.motion
    dur = motion.duration_param
    if motion.kind == 'velocity_timed':
        inputs = _motion_inputs(motion)
        params: list[ParamSpec] = []
        joint_tpl: list = []
        for inp in inputs:
            params.append(
                ParamSpec(
                    name=inp.name,
                    type='number',
                    description=inp.unit or inp.name,
                    required=inp.default is None,
                    default=inp.default,
                )
            )
            joint_tpl.append(f'${inp.name}')
        while len(joint_tpl) < 3:
            joint_tpl.append(0)
        params.append(
            ParamSpec(
                name=dur,
                type='number',
                description='duración del comando en segundos',
                required=False,
                default=2.0,
            )
        )
        refs = _ros_ref_names(schema, 'topic_pub', 'topic_sub')
        return ToolSpec(
            name='drive',
            description=(
                f'Mueve la base de {profile.display_name} con velocidades en el marco del robot '
                f'(cmd_vel): linear_x adelante(+)/atrás(-), angular_z giro CCW(+)/CW(-). '
                f'Solo recto sin girar: distancia ≈ linear_x × {dur}. No hay movimiento lateral.'
            ),
            parameters=tuple(params),
            bridge=BridgeAction(
                op='move_joints',
                joints_template=joint_tpl,
                seconds_param=dur,
                safety_max_step=False,
                safety_clamp=True,
                verify=motion.resolved_verify(),
            ),
            ros_refs=refs,
        )

    params = (
        ParamSpec(
            name='joints',
            type='array',
            description=f'Lista de {profile.dof} posiciones en radianes',
            required=True,
        ),
        ParamSpec(
            name=dur,
            type='number',
            description='tiempo de movimiento en segundos',
            required=False,
            default=4.0,
        ),
    )
    verify = motion.resolved_verify()
    return ToolSpec(
        name='move_to_joints',
        description=(
            f'Mueve el brazo {profile.display_name} a las posiciones articulares indicadas.'
        ),
        parameters=params,
        bridge=BridgeAction(
            op='move_joints',
            joints_template='$joints',
            seconds_param=dur,
            safety_max_step=True,
            safety_clamp=True,
            verify=verify,
        ),
        ros_refs=_ros_ref_names(schema, 'topic_pub', 'topic_sub'),
    )


def _home_tool(schema: AgentRosSchema, profile: RobotProfile) -> ToolSpec | None:
    if not profile.capabilities.home:
        return None
    pose = schema.state.representation == 'pose_2d'
    name = 'reset_sim' if pose else 'go_home'
    desc = (
        'Reinicia simulación / pose inicial del mapa (servicio reset ROS).'
        if pose
        else f'Lleva {profile.display_name} a la postura home del perfil JSON.'
    )
    return ToolSpec(
        name=name,
        description=desc,
        parameters=(),
        bridge=BridgeAction(
            op='home',
            verify='none' if pose else 'position',
            verify_target='home_pose' if not pose else None,
        ),
        ros_refs=_ros_ref_names(schema, 'service'),
    )


def _init_tool(schema: AgentRosSchema, profile: RobotProfile) -> ToolSpec | None:
    if not profile.capabilities.init:
        return None
    if schema.state.representation == 'pose_2d':
        return None
    return ToolSpec(
        name='go_init',
        description=f'Lleva {profile.display_name} a la postura init del perfil JSON.',
        parameters=(),
        bridge=BridgeAction(
            op='init',
            verify='position',
            verify_target='init_pose',
        ),
        ros_refs=(),
    )


def _gripper_tool(profile: RobotProfile) -> ToolSpec | None:
    if not profile.capabilities.gripper:
        return None
    return ToolSpec(
        name='set_gripper',
        description='Abre o cierra la pinza (1.0 abierto, 0.0 cerrado).',
        parameters=(
            ParamSpec(
                name='open',
                type='number',
                description='apertura 0..1',
                required=True,
            ),
        ),
        bridge=BridgeAction(op='gripper', verify='none'),
    )


def _torque_tool(profile: RobotProfile) -> ToolSpec | None:
    if not profile.capabilities.torque:
        return None
    return ToolSpec(
        name='set_torque',
        description='Enciende o apaga torque en los actuadores.',
        parameters=(
            ParamSpec(name='on', type='boolean', description='true=ON', required=True),
        ),
        bridge=BridgeAction(op='torque', verify='none'),
    )


def default_agent_rules(schema: AgentRosSchema) -> tuple[str, ...]:
    if schema.motion.kind == 'velocity_timed':
        return (
            'Responde en español, breve.',
            'Usa solo las tools listadas; no inventes nombres de brazo si el robot es móvil.',
            'Velocidades moderadas (linear_x ~0.2–0.5 m/s, seconds 1–4 s).',
            'Antes de rutas largas, lee la pose con la tool de estado.',
            'Una tool por paso lógico.',
        )
    return (
        'Responde en español, breve.',
        'Pasos articulares pequeños (~0.3 rad) salvo petición explícita.',
        'Antes de secuencias largas, lee estado con la tool de lectura.',
        'Confía en el texto que devuelven las tools.',
        'Una tool por paso lógico.',
    )


def generate_tool_specs(profile: RobotProfile, schema: AgentRosSchema) -> tuple[ToolSpec, ...]:
    specs: list[ToolSpec] = [_read_tool(schema, profile), _motion_tool(schema, profile)]
    for factory in (_home_tool, _init_tool):
        t = factory(schema, profile)
        if t:
            specs.append(t)
    for extra in (_gripper_tool(profile), _torque_tool(profile)):
        if extra:
            specs.append(extra)
    return tuple(specs)


def resolve_tool_specs(
    profile: RobotProfile,
    schema: AgentRosSchema,
    tools_field: Any,
) -> tuple[ToolSpec, ...]:
    if tools_field == 'auto' or tools_field is None:
        return generate_tool_specs(profile, schema)
    if isinstance(tools_field, list):
        from .tool_spec import ToolSpec as TS

        return tuple(TS.from_dict(t) for t in tools_field)
    raise ValueError('agent.tools debe ser "auto" o una lista de definiciones de tools')
