"""tests/conftest.py — shared fixtures, environment setup, and zero-dependency mock shims."""
from __future__ import annotations
import os
import sys
from types import ModuleType
from unittest.mock import MagicMock, AsyncMock
import pytest

# Prevent any real API calls from test env
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-placeholder")
os.environ.setdefault("VOYAGE_API_KEY", "")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-prod")

def _ensure_module(name: str):
    if name not in sys.modules:
        m = ModuleType(name)
        sys.modules[name] = m
    return sys.modules[name]

# Mock tenacity
if "tenacity" not in sys.modules:
    try:
        import tenacity
    except ImportError:
        tenacity_mod = _ensure_module("tenacity")
        def retry(*args, **kwargs):
            def decorator(fn):
                return fn
            return decorator
        tenacity_mod.retry = retry
        tenacity_mod.stop_after_attempt = lambda *a, **k: None
        tenacity_mod.wait_exponential = lambda *a, **k: None

# Mock langchain_core & messages
if "langchain_core" not in sys.modules:
    try:
        import langchain_core
    except ImportError:
        _ensure_module("langchain_core")
        lc_msg_mod = _ensure_module("langchain_core.messages")
        class BaseMsg:
            def __init__(self, content="", **kwargs):
                self.content = content
        class HumanMessage(BaseMsg): pass
        class SystemMessage(BaseMsg): pass
        lc_msg_mod.HumanMessage = HumanMessage
        lc_msg_mod.SystemMessage = SystemMessage

# Mock langchain_anthropic
if "langchain_anthropic" not in sys.modules:
    try:
        import langchain_anthropic
    except ImportError:
        la_mod = _ensure_module("langchain_anthropic")
        class ChatAnthropic:
            def __init__(self, *args, **kwargs):
                pass
            def with_structured_output(self, *args, **kwargs):
                m = MagicMock()
                m.ainvoke = AsyncMock()
                return m
        la_mod.ChatAnthropic = ChatAnthropic

# Mock langgraph & subpackages
if "langgraph" not in sys.modules:
    try:
        import langgraph
    except ImportError:
        _ensure_module("langgraph")
        lg_graph = _ensure_module("langgraph.graph")
        lg_graph.END = "__end__"
        class StateGraph:
            def __init__(self, state_schema=None):
                self.nodes = {}
                self.edges = []
            def add_node(self, name, node):
                self.nodes[name] = node
            def add_edge(self, start, end):
                self.edges.append((start, end))
            def add_conditional_edges(self, source, path, path_map=None):
                pass
            def set_entry_point(self, name):
                pass
            def compile(self, checkpointer=None):
                m = MagicMock()
                m.ainvoke = AsyncMock(return_value={})
                return m
        lg_graph.StateGraph = StateGraph

        _ensure_module("langgraph.checkpoint")
        _ensure_module("langgraph.checkpoint.postgres")
        lg_aio = _ensure_module("langgraph.checkpoint.postgres.aio")
        class AsyncPostgresSaver:
            @classmethod
            def from_conn_string(cls, *args, **kwargs):
                return MagicMock()
        lg_aio.AsyncPostgresSaver = AsyncPostgresSaver

# Mock qdrant_client
if "qdrant_client" not in sys.modules:
    try:
        import qdrant_client
    except ImportError:
        qc_mod = _ensure_module("qdrant_client")
        class AsyncQdrantClient:
            def __init__(self, *args, **kwargs):
                pass
            async def search(self, *args, **kwargs):
                return []
        qc_mod.AsyncQdrantClient = AsyncQdrantClient
        qc_models = _ensure_module("qdrant_client.models")
        qc_models.Distance = MagicMock()
        qc_models.VectorParams = MagicMock()
        qc_models.Filter = MagicMock()
        qc_models.FieldCondition = MagicMock()
        qc_models.MatchValue = MagicMock()
        qc_models.PointStruct = MagicMock()
        qc_mod.models = qc_models
