"""Proveedor LLM (Gemini, Groq u OpenAI) con tool calling."""
from __future__ import annotations

import os

from langchain_core.language_models.chat_models import BaseChatModel


def _google_api_key() -> str | None:
    return os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')


def has_llm_credentials() -> bool:
    return bool(
        _google_api_key()
        or os.environ.get('GROQ_API_KEY')
        or os.environ.get('OPENAI_API_KEY')
    )


def _resolved_provider() -> str:
    from .env_config import load_agent_dotenv

    load_agent_dotenv()
    explicit = os.environ.get('LLM_PROVIDER', '').strip().lower()
    if explicit in ('gemini', 'google'):
        return 'gemini'
    if explicit == 'openai':
        return 'openai'
    if explicit == 'groq':
        return 'groq'
    if _google_api_key():
        return 'gemini'
    if os.environ.get('GROQ_API_KEY'):
        return 'groq'
    if os.environ.get('OPENAI_API_KEY'):
        return 'openai'
    return 'none'


def llm_provider_name() -> str:
    return _resolved_provider()


def llm_model_name() -> str:
    provider = _resolved_provider()
    if provider == 'gemini':
        return os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash-lite')
    if provider == 'groq':
        return os.environ.get('GROQ_MODEL', 'openai/gpt-oss-20b')
    if provider == 'openai':
        return os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
    return ''


def build_chat_model() -> BaseChatModel:
    provider = _resolved_provider()
    if provider == 'gemini':
        key = _google_api_key()
        if not key:
            raise RuntimeError(
                'Falta API key: define GOOGLE_API_KEY o GEMINI_API_KEY en agent/.env'
            )
        from langchain_google_genai import ChatGoogleGenerativeAI

        model = os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash-lite')
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=key,
            temperature=0,
            max_retries=2,
        )

    if provider == 'groq':
        from langchain_groq import ChatGroq

        model = os.environ.get('GROQ_MODEL', 'openai/gpt-oss-20b')
        return ChatGroq(model=model, temperature=0, max_retries=2)

    key = os.environ.get('OPENAI_API_KEY')
    if not key:
        raise RuntimeError(
            'Falta API key: define GOOGLE_API_KEY, GROQ_API_KEY u OPENAI_API_KEY en agent/.env'
        )
    from langchain_openai import ChatOpenAI

    model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
    return ChatOpenAI(model=model, temperature=0, timeout=60)
