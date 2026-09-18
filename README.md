# OMX Chat Framework

Control del brazo ROBOTIS OMX-F por chat de tareas en español natural.
Arquitectura: Chat UI + agente reactivo (LangGraph-ready) + bridge ROS → HTTP.

```
┌──────────────┐   HTTP :8501   ┌──────────────┐   HTTP :8000   ┌──────────────────┐
│  Chat UI     │ ─────────────▶ │  Agente      │ ─────────────▶ │  Bridge FastAPI  │──▶ robot OMX-F
│ (navegador)  │                │ parse→validate→execute→observe │  (docker Jazzy)  │    /dev/ttyACM0
└──────────────┘                └──────────────┘                └──────────────────┘
```

## Piezas

| Carpeta | Qué es | Dónde corre |
|---|---|---|
| `bridge/omx_bridge.py` | FastAPI: `/state`, `/move_joints`, `/home`, `/init`, `/gripper`, `/torque`, `/reboot` | dentro del container `open_manipulator` (`/workspace`, ROS 2 Jazzy + zenoh) |
| `agent/tools.py` | Cliente HTTP del bridge + límites de seguridad | host |
| `agent/graph_mini.py` | Grafo reactivo `parse → validate → execute → observe`. Cadena LLM: OpenAI → Gemini → reglas locales | host |
| `agent/server.py` | Chat UI (solo stdlib, puerto 8501) | host |

## Requisitos

- PC con Ubuntu + Docker
- Repo `ROBOTIS-GIT/open_manipulator` con su container (`robotis/open-manipulator`)
- Brazo OMX-F conectado por USB (`/dev/ttyACM0`, 1 Mbps) + fuente 12 V
- Python 3.10+ en host (el bridge usa el Python 3.12 del container, ya trae `fastapi`+`uvicorn`)
- (Opcional) API key OpenAI o Gemini para lenguaje libre

## Instalación

```bash
# 0) Clona este repo
git clone https://github.com/Javieryahir/omx-framework.git
cd omx-framework

# 1) Bridge: cópialo al workspace del container (se monta en /workspace)
docker cp bridge/omx_bridge.py open_manipulator:/workspace/omx_bridge.py

# 2) (Opcional) LLM: crea agent/.env con tus keys (NUNCA se sube a git)
cat > agent/.env <<'EOF'
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...
EOF
chmod 600 agent/.env
```

## Uso

```bash
# 1) Dentro del container: bringup + bridge (puertos 8000)
# (en terminales dentro del container con ROS_DOMAIN_ID=30 y RMW zenoh)
ros2 launch open_manipulator_bringup omx_f.launch.py port_name:=/dev/ttyACM0
python3 /workspace/omx_bridge.py

# 2) En host, desde la carpeta del repo:
python3 -m agent.server   # :8501

# 3) Abre http://localhost:8501 y pide tareas:
#    estado · home · init · gira un poco · mueve j1 a 0.5
#    joints [0,-1.57,1.57,1.57,0] · abre la pinza
#    secuencia: home, abre, cierra
```

## Seguridad

- `agent/.env` con las API keys: **no se commitea** (ver `.gitignore`).
- Límites de joints validados antes de mover; el agente verifica la
  posición real después de cada movimiento y reporta discrepancias.
- El robot SE MUEVE con cada tarea: deja área libre y empieza con
  movimientos pequeños (`gira un poco` ≈ 0.3 rad ≈ 17°).
