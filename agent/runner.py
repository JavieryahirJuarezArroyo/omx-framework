"""Punto de entrada: solo agente LangGraph (LLM + tools obligatorio)."""
from __future__ import annotations

from .llm import has_llm_credentials, llm_model_name, llm_provider_name


def active_mode(mode: str | None = None) -> str:
    return 'agent'


def llm_status() -> dict:
    from .env_config import langsmith_status

    return {
        'mode': 'agent',
        'provider': llm_provider_name(),
        'model': llm_model_name(),
        'langsmith': langsmith_status(),
    }


def _require_llm_config() -> None:
    if not has_llm_credentials():
        raise RuntimeError(
            'Falta API key: GROQ_API_KEY o OPENAI_API_KEY en agent/.env'
        )


def run(text: str, mode: str | None = None, session_id: str | None = None) -> str:
    _require_llm_config()
    try:
        from .graph import run_agent

        return run_agent(text, session_id=session_id)
    except ImportError as e:
        return (
            'Dependencias del agente no instaladas. Ejecuta: pip install -e ".[agent]" '
            f'({e})'
        )
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f'error agente LangGraph: {e}'
