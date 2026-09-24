# Tools dinámicas (agent.ros)

El framework **no** hardcodea tools por robot. Al cargar `configs/robots/*.json`:

1. Lee **`agent.ros`** (interfaces ROS + `state` + `motion`).
2. Ejecuta **`tool_codegen`** → lista de `ToolSpec`.
3. **`tool_runtime`** construye `StructuredTool` de LangChain y ejecuta ops del bridge HTTP.

## Esquema `agent.ros`

```json
"agent": {
  "tools": "auto",
  "ros": {
    "interfaces": [
      { "kind": "topic_sub", "name": "/turtle1/pose", "msg_type": "turtlesim/msg/Pose" },
      { "kind": "topic_pub", "name": "/turtle1/cmd_vel", "msg_type": "geometry_msgs/msg/Twist" },
      { "kind": "service", "name": "/reset", "srv_type": "std_srvs/srv/Empty" }
    ],
    "state": { "representation": "pose_2d" },
    "motion": {
      "kind": "velocity_timed",
      "duration_param": "seconds",
      "inputs": [
        { "name": "linear_x", "unit": "m/s", "bridge_index": 0 },
        { "name": "angular_z", "unit": "rad/s", "bridge_index": 1, "default": 0 }
      ]
    }
  }
}
```

### `state.representation`

| Valor      | Tool de lectura generada | Salida |
|------------|--------------------------|--------|
| `pose_2d`  | `get_pose`               | x, y, theta |
| `joints`   | `get_robot_state`        | arm[], joint_names |

### `motion.kind`

| Valor              | Tool de movimiento | Bridge |
|--------------------|--------------------|--------|
| `velocity_timed`   | `drive`            | POST `/move_joints` con [linear_x, angular_z, 0] |
| `joint_positions`  | `move_to_joints`   | POST `/move_joints` con lista DOF |

`capabilities` añaden `set_gripper`, `set_torque`, `go_home` / `reset_sim`, `go_init` según corresponda.

## Tools manuales (avanzado)

`"tools": [ { "name": "...", "description": "...", "parameters": [...], "bridge": { "op": "..." } } ]`

sustituye la generación automática (misma forma que produce el codegen internamente).

## Prompt

`prompts.build_system_prompt()` lista tools generadas + interfaces ROS + reglas (`agent.behavior.rules` o defaults según `motion.kind`).

## Próximo paso: catálogo ROS en el bridge

El edge puede exponer `GET /ros/catalog` (topics/servicios reales) y un script puede **rellenar** `agent.ros.interfaces` en el JSON; el agente sigue sin ejecutar ROS localmente.
