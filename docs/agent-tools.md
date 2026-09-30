# Tools dinámicas (agent.ros)

El framework **no** hardcodea tools por robot. Al cargar `configs/robots/*.json`:

1. Lee **`agent.ros`** (interfaces ROS + `state` + `motion` + opcional `bindings`).
2. Ejecuta **`tool_codegen`** → lista de `ToolSpec`.
3. **`tool_runtime`** construye `StructuredTool` de LangChain y ejecuta ops vía **`Ros2Adapter`** (rclpy).

## Esquema `agent.ros`

```json
"agent": {
  "tools": "auto",
  "introspection": true,
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
    },
    "bindings": {
      "trajectory": {
        "name": "/arm_controller/follow_joint_trajectory",
        "type": "control_msgs/action/FollowJointTrajectory"
      }
    }
  }
}
```

Si `bindings` se omite, se **infieren** topics/servicios desde `interfaces` y defaults razonables para brazo OMX (`agent/ros_bindings.py`).

### `state.representation`

| Valor      | Tool de lectura generada | Salida |
|------------|--------------------------|--------|
| `pose_2d`  | `get_pose`               | x, y, theta |
| `joints`   | `get_robot_state`        | arm[], joint_names |

### `motion.kind`

| Valor              | Tool de movimiento | ROS |
|--------------------|--------------------|-----|
| `velocity_timed`   | `drive`            | publica `Twist` en `topic_pub` |
| `joint_positions`  | `move_to_joints`   | action `FollowJointTrajectory` |

`capabilities` añaden `set_gripper`, `set_torque`, `go_home` / `reset_sim`, `go_init`.

## Tools manuales (avanzado)

`"tools": [ { "name": "...", "description": "...", "parameters": [...], "bridge": { "op": "..." } } ]`

sustituye la generación automática.

## Introspección ROS 2

Con `"introspection": true` se añaden tools de solo lectura (`ros2_topic_list`, `ros2_node_list`, …) vía CLI `ros2`, similar al kit de ROSA.

## Prompt

`prompts.build_system_prompt()` lista tools generadas + interfaces ROS + reglas (`agent.behavior.rules` o defaults según `motion.kind`).
