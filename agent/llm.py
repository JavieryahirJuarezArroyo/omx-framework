"""Proveedor LLM (Groq u OpenAI) con tool calling."""
from __future__ import annotations

import os

from langchain_core.language_models.chat_models import BaseChatModel


def has_llm_credentials() -> bool:
    return bool(os.environ.get('GROQ_API_KEY') or os.environ.get('OPENAI_API_KEY'))


def llm_provider_name() -> str:
    if os.environ.get('GROQ_API_KEY') and os.environ.get('LLM_PROVIDER', 'groq').lower() != 'openai':
        return 'groq'
    if os.environ.get('OPENAI_API_KEY'):
        return 'openai'
    return 'none'


def llm_model_name() -> str:
    from .env_config import load_agent_dotenv

    load_agent_dotenv()
    if llm_provider_name() == 'groq':
        return os.environ.get('GROQ_MODEL', 'openai/gpt-oss-20b')
    if llm_provider_name() == 'openai':
        return os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
    return ''


def build_chat_model() -> BaseChatModel:
    from .env_config import load_agent_dotenv

    load_agent_dotenv()
    if os.environ.get('GROQ_API_KEY') and os.environ.get('LLM_PROVIDER', 'groq').lower() != 'openai':
        from langchain_groq import ChatGroq

        # Groq retira modelos con frecuencia; gpt-oss-20b suele estar disponible en tier gratis.
        model = os.environ.get('GROQ_MODEL', 'openai/gpt-oss-20b')
        return ChatGroq(model=model, temperature=0, max_retries=2)

    key = os.environ.get('OPENAI_API_KEY')
    if not key:
        raise RuntimeError(
            'Falta API key: define GROQ_API_KEY o OPENAI_API_KEY en agent/.env'
        )
    from langchain_openai import ChatOpenAI

    model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
    return ChatOpenAI(model=model, temperature=0, timeout=60)
