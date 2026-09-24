"""Variables de entorno (ROS_AGENT_* con compatibilidad OMX_*)."""
from __future__ import annotations

import os
from pathlib import Path

_DOTENV_KEYS = frozenset(
    {
        'LLM_PROVIDER',
        'GROQ_API_KEY',
        'GROQ_MODEL',
        'OPENAI_API_KEY',
        'OPENAI_MODEL',
        'LANGCHAIN_TRACING_V2',
        'LANGCHAIN_API_KEY',
        'LANGCHAIN_PROJECT',
        'LANGCHAIN_ENDPOINT',
        'LANGSMITH_API_KEY',
        'LANGSMITH_PROJECT',
        'LANGSMITH_TRACING',
    }
)


def load_agent_dotenv() -> None:
    """Carga agent/.env; sobrescribe claves LLM (evita GROQ_MODEL obsoleto en el shell)."""
    path = Path(__file__).resolve().parent / '.env'
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding='utf-8')
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()
        if key in _DOTENV_KEYS:
            os.environ[key] = value
        else:
            os.environ.setdefault(key, value)
    configure_langsmith_tracing()


def configure_langsmith_tracing() -> bool:
    """Activa trazas LangSmith si hay API key (LANGCHAIN_* o LANGSMITH_*)."""
    api_key = os.environ.get('LANGCHAIN_API_KEY') or os.environ.get('LANGSMITH_API_KEY')
    if not api_key:
        return False
    os.environ['LANGCHAIN_API_KEY'] = api_key

    project = os.environ.get('LANGCHAIN_PROJECT') or os.environ.get('LANGSMITH_PROJECT')
    if project:
        os.environ.setdefault('LANGCHAIN_PROJECT', project)
    else:
        os.environ.setdefault('LANGCHAIN_PROJECT', 'omx-framework')

    tracing = (
        os.environ.get('LANGCHAIN_TRACING_V2', '').lower() in ('1', 'true', 'yes')
        or os.environ.get('LANGSMITH_TRACING', '').lower() in ('1', 'true', 'yes')
    )
    if not tracing:
        os.environ['LANGCHAIN_TRACING_V2'] = 'true'
    return True


def langsmith_status() -> dict[str, str | bool]:
    enabled = configure_langsmith_tracing()
    return {
        'tracing': enabled and os.environ.get('LANGCHAIN_TRACING_V2', '').lower() == 'true',
        'project': os.environ.get('LANGCHAIN_PROJECT', '') if enabled else '',
        'endpoint': os.environ.get('LANGCHAIN_ENDPOINT', 'https://api.smith.langchain.com'),
    }


_ENV_KEYS: dict[str, list[str]] = {
    'MAX_STEP': ['ROS_AGENT_MAX_STEP', 'OMX_MAX_STEP'],
    'MAX_ITERATIONS': ['ROS_AGENT_MAX_ITERATIONS', 'OMX_MAX_ITERATIONS'],
    'TOL': ['ROS_AGENT_TOL', 'OMX_TOL'],
    'ROBOT': ['ROS_AGENT_ROBOT', 'OMX_ROBOT'],
    'CONFIG': ['ROS_AGENT_CONFIG', 'OMX_CONFIG'],
    'BRIDGE': ['ROS_AGENT_BRIDGE', 'OMX_BRIDGE', 'OMX_BRIDGE_URL'],
}


def env(name: str, default: str | None = None) -> str | None:
    keys = _ENV_KEYS.get(name, [f'ROS_AGENT_{name}', f'OMX_{name}'])
    for key in keys:
        val = os.environ.get(key)
        if val is not None and val != '':
            return val
    return default
