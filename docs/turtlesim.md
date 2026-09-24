# turtlesim + omx-framework

El bridge traduce el **contrato REST** del framework a `/turtle1/cmd_vel` y `/turtle1/pose`. Las tools del agente se **generan** desde `configs/robots/turtlesim.json` → `agent.ros` (no hay preset “turtlesim” en código).

## Perfil relevante

| Campo | Valor |
|-------|--------|
| `agent.ros.state.representation` | `pose_2d` → tool `get_pose` |
| `agent.ros.motion.kind` | `velocity_timed` → tool `drive` |
| `capabilities.home` | tool `reset_sim` → POST `/home` → `/reset` |

`GET /state` del bridge sigue devolviendo `{ "arm": [x, y, theta] }` (clave genérica del contrato HTTP).

## Docker / agente

Ver pasos en la sección anterior del repo (`docker/turtlesim/`, `ROS_AGENT_ROBOT=turtlesim`, chat :8501).

## Frases de prueba (LLM)

- "¿dónde estás?" → `get_pose`
- "vuelve al centro" → `reset_sim`
- "avanza ~1 metro recto" → `drive` (linear_x × seconds ≈ distancia)
- "gira a la izquierda" → `drive` con `angular_z` negativo
