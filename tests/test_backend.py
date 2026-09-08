import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

from langgraph.checkpoint.postgres import PostgresSaver


@pytest.fixture
def backend_module(monkeypatch):
    """Import backend.py with the DB connection and checkpointer setup mocked
    out, so tests don't hit the real Supabase DB or require live credentials.

    PostgresSaver itself is left as the real class (not a MagicMock) because
    LangGraph's graph.compile() does an isinstance(checkpointer,
    BaseCheckpointSaver) check that a mock object would fail."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/testdb")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

    with patch("psycopg.connect", return_value=MagicMock()), \
         patch.object(PostgresSaver, "setup", lambda self: None):
        sys.modules.pop("backend", None)
        module = importlib.import_module("backend")
        yield module

    sys.modules.pop("backend", None)


# ---------------------------------------------------------------------------
# get_database_url
# ---------------------------------------------------------------------------

def test_get_database_url_missing_raises(backend_module, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="DATABASE_URL is missing"):
        backend_module.get_database_url()


def test_get_database_url_appends_sslmode(backend_module, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host:5432/db")
    result = backend_module.get_database_url()
    assert result == "postgresql://u:p@host:5432/db?sslmode=require"


def test_get_database_url_preserves_existing_sslmode(backend_module, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host:5432/db?sslmode=disable")
    result = backend_module.get_database_url()
    assert result.count("sslmode=") == 1
    assert "sslmode=disable" in result


def test_get_database_url_uses_ampersand_when_query_present(backend_module, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host:5432/db?foo=bar")
    result = backend_module.get_database_url()
    assert result == "postgresql://u:p@host:5432/db?foo=bar&sslmode=require"


# ---------------------------------------------------------------------------
# run_travel_agent
# ---------------------------------------------------------------------------

def test_run_travel_agent_generates_thread_id_when_absent(backend_module, monkeypatch):
    fake_result = {
        "messages": [MagicMock(content="Final answer text")],
        "flight_results": "flights",
        "hotel_results": "hotels",
        "itinerary": "itinerary text",
        "llm_calls": 4,
    }
    monkeypatch.setattr(
        backend_module.travel_graph, "invoke", lambda state, config: fake_result
    )

    result = backend_module.run_travel_agent("plan a trip")

    assert result["answer"] == "Final answer text"
    assert result["thread_id"].startswith("user_")
    assert result["flight_results"] == "flights"
    assert result["hotel_results"] == "hotels"
    assert result["itinerary"] == "itinerary text"
    assert result["llm_calls"] == 4


def test_run_travel_agent_uses_provided_thread_id(backend_module, monkeypatch):
    fake_result = {"messages": [MagicMock(content="ok")]}
    monkeypatch.setattr(
        backend_module.travel_graph, "invoke", lambda state, config: fake_result
    )

    result = backend_module.run_travel_agent("hello", thread_id="fixed-id")

    assert result["thread_id"] == "fixed-id"


def test_run_travel_agent_passes_thread_id_in_config(backend_module, monkeypatch):
    captured = {}

    def fake_invoke(state, config):
        captured["config"] = config
        return {"messages": [MagicMock(content="ok")]}

    monkeypatch.setattr(backend_module.travel_graph, "invoke", fake_invoke)

    backend_module.run_travel_agent("hello", thread_id="abc-123")

    assert captured["config"]["configurable"]["thread_id"] == "abc-123"
