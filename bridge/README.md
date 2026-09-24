# Bridge HTTP sobre ROS

El **host del agente no ejecuta ROS**. Un proceso en el robot, en Docker o en un edge publica una API REST; el framework se conecta con el adapter `http`.

## Contrato REST (mínimo)

| Método | Ruta | Cuerpo | Respuesta |
|--------|------|--------|-----------|
| GET | `/health` | — | `{ "ok": true }` (cualquier JSON) |
| GET | `/state` | — | `{ "arm": [float×DOF], "gripper": 0..1 opcional }` |
| POST | `/move_joints` | `{ "joints": [...], "seconds": 4.0 }` | JSON de ack |
| POST | `/home` | — | JSON de ack |
| POST | `/init` | — | JSON de ack |
| POST | `/gripper` | `{ "open": 0..1, "seconds": 2.0 }` | opcional si `capabilities.gripper` |
| POST | `/torque` | `{ "on": true }` | opcional si `capabilities.torque` |

Claves `arm` / `gripper` se pueden renombrar en el JSON del robot (`state_arm_key`, `state_gripper_key`).

## Implementaciones de ejemplo

| Bridge | Robot |
|--------|--------|
| [`omx_bridge.py`](omx_bridge.py) | OpenMANIPULATOR OMX-F (ROS 2 Jazzy) |
| [`turtlesim_bridge.py`](turtlesim_bridge.py) | ROS 2 turtlesim (`cmd_vel` + pose) → ver [docs/turtlesim.md](../docs/turtlesim.md) |

## Configuración del agente

```bash
export ROS_AGENT_ROBOT=open_manipulator_omx_f
# o
export ROS_AGENT_CONFIG=configs/robots/mi_robot.json
export ROS_AGENT_BRIDGE=http://192.168.1.10:8000   # sobrescribe base_url si lo añades en .env vía JSON edit
```

Edita `adapter.base_url` en el JSON del robot o usa el mismo host que el bridge.
