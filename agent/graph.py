"""LangGraph ReAct: agent <-> tools (robot vía adapter configurable)."""
from __future__ import annotations

import os
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from .context import get_profile
from .env_config import env
from .prompts import build_system_prompt
from .llm import build_chat_model, has_llm_credentials
from .tools_lc import get_agent_tools

_graph = None
_sessions: dict[str, list] = {}
_graph_robot_id: str | None = None


def _message_content_text(content: Any) -> str:
    """Gemini (y otros) devuelven content como str o lista de bloques."""
    if content is None:
        return ''
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get('type') == 'text' and block.get('text'):
                    parts.append(str(block['text']))
                elif block.get('text') is not None:
                    parts.append(str(block['text']))
            else:
                text = getattr(block, 'text', None)
                if text is not None:
                    parts.append(str(text))
        return '\n'.join(p for p in parts if p)
    return str(content)


def reset_graph() -> None:
    global _graph, _graph_robot_id, _sessions
    _graph = None
    _graph_robot_id = None
    _sessions.clear()


def _max_iterations() -> int:
    return int(env('MAX_ITERATIONS', '15'))


def _get_graph():
    global _graph, _graph_robot_id
    p = get_profile()
    rid = f'{p.id}:{p.tools_fingerprint}'
    if _graph is not None and _graph_robot_id == rid:
        return _graph
    agent_tools = get_agent_tools()
    llm = build_chat_model().bind_tools(agent_tools)

    def agent_node(state: MessagesState) -> dict[str, Any]:
        response = llm.invoke(state['messages'])
        return {'messages': [response]}

    builder = StateGraph(MessagesState)
    builder.add_node('agent', agent_node)
    builder.add_node('tools', ToolNode(agent_tools))
    builder.add_edge(START, 'agent')
    builder.add_conditional_edges('agent', tools_condition)
    builder.add_edge('tools', 'agent')
    _graph = builder.compile()
    _graph_robot_id = rid
    return _graph


def _session_messages(session_id: str) -> list:
    if session_id not in _sessions:
        _sessions[session_id] = [SystemMessage(content=build_system_prompt())]
    return _sessions[session_id]


def clear_session(session_id: str = 'default') -> None:
    _sessions.pop(session_id, None)


def run_agent(user_text: str, session_id: str | None = None) -> str:
    from .env_config import load_agent_dotenv

    load_agent_dotenv()
    sid = session_id or 'default'
    if not has_llm_credentials():
        raise RuntimeError('GOOGLE_API_KEY, GROQ_API_KEY u OPENAI_API_KEY requerida (agent/.env).')
    messages = _session_messages(sid)
    if isinstance(messages[0], SystemMessage):
        messages[0] = SystemMessage(content=build_system_prompt())
    messages.append(HumanMessage(content=user_text))
    graph = _get_graph()
    steps = max(_max_iterations() * 2, 40)
    result = graph.invoke({'messages': messages}, {'recursion_limit': steps})
    _sessions[sid] = list(result['messages'])
    last = result['messages'][-1]
    if isinstance(last, AIMessage):
        text = _message_content_text(last.content).strip()
        return text or '(sin respuesta textual)'
    return str(last)
