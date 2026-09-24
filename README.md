# ROS Agent Framework

Framework **agnóstico al robot**: agente **LangGraph ReAct** (OpenAI obligatorio) conectado a **ROS** vía **bridge HTTP**. Perfil por JSON en `configs/robots/`.

```
┌──────────────┐   HTTP :8501   ┌──────────────┐   HTTP (config)   ┌─────────────────┐
│  Chat UI     │ ─────────────▶ │  LLM Agent   │ ────────────────▶ │  Bridge REST    │──▶ ROS 2 / robot
└──────────────┘                └──────────────┘                   └─────────────────┘
```

## Requisitos

- Python 3.10+
- `pip install -e ".[agent]"` (langgraph, langchain-openai)
- **`OPENAI_API_KEY`** en `agent/.env` o entorno (obligatorio)
- Bridge HTTP del robot (ej. `bridge/omx_bridge.py`, `turtlesim_bridge.py`)

## Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `OPENAI_API_KEY` | **Obligatoria** |
| `OPENAI_MODEL` | Default `gpt-4o-mini` |
| `ROS_AGENT_ROBOT` | Id del JSON en `configs/robots/` |
| `ROS_AGENT_CONFIG` | Ruta explícita al JSON |
| `ROS_AGENT_BRIDGE` | Sobrescribe `adapter.base_url` |
| `ROS_AGENT_MAX_STEP` | Máx. radianes por paso (brazos) |
| `ROS_AGENT_MAX_ITERATIONS` | Pasos ReAct (default 15) |
| `LANGCHAIN_TRACING_V2` | `true` para enviar trazas a [LangSmith](https://smith.langchain.com) |
| `LANGCHAIN_API_KEY` | API key LangSmith (`lsv2_...`) |
| `LANGCHAIN_PROJECT` | Proyecto en LangSmith (default `omx-framework`) |

Prefijo legacy `OMX_*` también aceptado (excepto modos command/auto, eliminados).

## Uso

```bash
git clone https://github.com/Javieryahir/omx-framework.git
cd omx-framework
pip install -e ".[agent]"

# agent/.env → OPENAI_API_KEY=sk-...
export ROS_AGENT_ROBOT=open_manipulator_omx_f
python -m agent.server   # http://localhost:8501
```

## Demo turtlesim

1. Bridge: `docker start omx-turtlesim-run` (o ver [docs/turtlesim.md](docs/turtlesim.md))
2. Agente: `.\scripts\run-turtlesim-agent.ps1` → http://localhost:8501

Perfil: `configs/robots/turtlesim.json` (`tools: auto` → `get_pose`, `drive`, `reset_sim`).

## Estructura

| Ruta | Rol |
|------|-----|
| `agent/graph.py` | LangGraph ReAct |
| `agent/tools_lc.py` | Tools LangChain desde perfil |
| `agent/runner.py` | Entrada única → `run_agent` |
| `configs/robots/*.json` | Robot + `agent.ros` → tools generadas + bridge URL |

## Seguridad

- El LLM mueve el robot real vía tools; límites en `safety.py` + perfil JSON
- No commitear `agent/.env`
