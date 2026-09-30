# ROS Agent Framework

Framework **agnóstico al robot**: agente **LangGraph ReAct** (OpenAI/Groq) con **ROS 2 en el mismo proceso** (`rclpy`). Perfil por JSON en `configs/robots/`.

```
┌──────────────┐   HTTP :8501   ┌──────────────────────────────────────┐
│  Chat UI     │ ─────────────▶ │  LangGraph + Ros2Adapter (rclpy)     │──▶ ROS 2 / robot
└──────────────┘                └──────────────────────────────────────┘
```

El agente debe correr **en el mismo entorno ROS** que el robot (contenedor sourcado o PC con Humble/Jazzy).

## Requisitos

- Python 3.10+
- ROS 2 (Humble+), `rclpy` y mensajes del robot disponibles en el entorno
- `pip install -e ".[agent]"` (langgraph, langchain-openai)
- **`OPENAI_API_KEY`** o **`GROQ_API_KEY`** en `agent/.env` o entorno

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `OPENAI_API_KEY` / `GROQ_API_KEY` | **Obligatoria** (una de las dos) |
| `OPENAI_MODEL` / `GROQ_MODEL` | Modelo LLM |
| `ROS_AGENT_ROBOT` | Id del JSON en `configs/robots/` |
| `ROS_AGENT_CONFIG` | Ruta explícita al JSON |
| `ROS_AGENT_MAX_STEP` | Máx. radianes por paso (brazos) |
| `ROS_AGENT_MAX_ITERATIONS` | Pasos ReAct (default 15) |
| `LANGCHAIN_TRACING_V2` | Trazas LangSmith |

Prefijo legacy `OMX_*` también aceptado.

## Uso

```bash
git clone https://github.com/Javieryahir/omx-framework.git
cd omx-framework
source /opt/ros/humble/setup.bash   # o tu distro
pip install -e ".[agent]"

export ROS_AGENT_ROBOT=open_manipulator_omx_f
python -m agent.server   # http://localhost:8501
```

## Demo turtlesim (Docker)

```powershell
.\scripts\run-turtlesim-agent.ps1
```

Contenedor: `turtlesim_node` + agente con `ROS_AGENT_ROBOT=turtlesim` → chat en http://localhost:8502. Ver [docs/turtlesim.md](docs/turtlesim.md).

## Demo OMX-F follower (Docker Jazzy)

```powershell
.\scripts\run-omx-follower-agent.ps1
```

Imagen Ubuntu + ROS 2 Jazzy + `open_manipulator` + agente. Por defecto **mock** (sin USB). Chat: http://localhost:8503. Ver [docs/omx-follower.md](docs/omx-follower.md).

## Conectar otro robot

1. Copia `configs/robots/generic_arm.json` → `mi_robot.json`.
2. Define `robot.*`, `capabilities`, `agent.ros.interfaces`.
3. Opcional: `agent.ros.bindings` (actions/servicios) si la inferencia automática no basta.
4. `"agent": { "introspection": true }` añade tools `ros2_topic_list`, etc. (estilo ROSA, solo lectura).
5. Arranca `python -m agent.server` **dentro** del workspace ROS del robot.

## Comparación rápida

| Enfoque | OMX (este repo) | ROSA | ROS-LLM | ROSClaw |
|---------|-----------------|------|---------|---------|
| Conexión | JSON + rclpy | `@tool` Python + CLI ros2 | Nodo + servicio function-call | MCP + daemon |
| Agente sin ROS | No | No | No | Sí (MCP remoto) |
| Tools generadas | Sí (`agent.ros`) | Parcial (kit ros2) | Manual (lista funciones) | Skills/MCP |

## Estructura

| Ruta | Rol |
|------|-----|
| `agent/graph.py` | LangGraph ReAct |
| `agent/adapter/ros2_adapter.py` | Bridge ROS 2 (topics/actions) |
| `agent/ros_bindings.py` | Bindings explícitos + inferencia |
| `agent/tools_lc.py` | Tools LangChain desde perfil |
| `configs/robots/*.json` | Robot + `agent.ros` |

## Seguridad

- El LLM mueve el robot real vía tools; límites en `safety.py` + perfil JSON
- No commitear `agent/.env`
