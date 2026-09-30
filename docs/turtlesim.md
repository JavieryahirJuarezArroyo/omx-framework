# turtlesim + omx-framework

El agente es un **nodo ROS 2** (`Ros2Adapter`): suscribe `/turtle1/pose`, publica `/turtle1/cmd_vel` y llama `/reset`. Las tools se **generan** desde `configs/robots/turtlesim.json` → `agent.ros`.

## Perfil relevante

| Campo | Valor |
|-------|--------|
| `adapter.type` | `ros2` |
| `agent.ros.state.representation` | `pose_2d` → tool `get_pose` |
| `agent.ros.motion.kind` | `velocity_timed` → tool `drive` |
| `capabilities.home` | tool `reset_sim` → servicio `/reset` |

Estado interno del adapter: `{ "arm": [x, y, theta] }` (clave genérica para la UI).

## Docker / agente

```powershell
.\scripts\run-turtlesim-agent.ps1
```

Imagen: `docker/turtlesim/Dockerfile` — `turtlesim_node` + `python -m agent.server` en `:8501`.

## Frases de prueba (LLM)

- "¿dónde estás?" → `get_pose`
- "vuelve al centro" → `reset_sim`
- "avanza ~1 metro recto" → `drive` (linear_x × seconds ≈ distancia)
- "gira a la izquierda" → `drive` con `angular_z` positivo
