"""Tests for agents.cities.search_cities.

The Databricks Vector Search client and the OpenAI-compatible LLM client are
both imported lazily inside search_cities, so we swap fake modules into
sys.modules. These run offline and need no credentials.
Run with:  pytest tests/test_cities.py -v
"""

import json
import sys
import types

from agents.cities import search_cities

# A representative similarity_search() response: columns declared in the
# manifest, rows returned as [content, title] in that same order.
_SAMPLE_SEARCH = {
    "manifest": {"columns": [{"name": "content"}, {"name": "title"}]},
    "result": {
        "data_array": [
            ["Kyoto is known for its temples and gardens.", "Kyoto"],
            ["Osaka is famous for street food and castles.", "Osaka"],
        ]
    },
}


def _invoke(query="coastal cities in Japan"):
    """Call the LangChain tool the way an agent would."""
    return search_cities.invoke({"query": query})


def _install_fakes(monkeypatch, *, search_result, summary="A lovely summary."):
    """Register fake databricks/openai modules for the lazy imports.

    ``search_result`` and ``summary`` may each be an Exception instance, in
    which case the corresponding fake raises it.
    """

    class _FakeIndex:
        def similarity_search(self, **kwargs):
            if isinstance(search_result, Exception):
                raise search_result
            return search_result

    class _FakeVectorSearchClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def get_index(self, **kwargs):
            return _FakeIndex()

    dbx = types.ModuleType("databricks")
    dbx_ai = types.ModuleType("databricks.ai_search")
    dbx_client = types.ModuleType("databricks.ai_search.client")
    dbx_client.VectorSearchClient = _FakeVectorSearchClient
    monkeypatch.setitem(sys.modules, "databricks", dbx)
    monkeypatch.setitem(sys.modules, "databricks.ai_search", dbx_ai)
    monkeypatch.setitem(sys.modules, "databricks.ai_search.client", dbx_client)

    class _FakeMessage:
        def __init__(self, content):
            self.content = content

    class _FakeChoice:
        def __init__(self, content):
            self.message = _FakeMessage(content)

    class _FakeCompletion:
        def __init__(self, content):
            self.choices = [_FakeChoice(content)]

    class _FakeCompletions:
        def create(self, **kwargs):
            if isinstance(summary, Exception):
                raise summary
            return _FakeCompletion(summary)

    class _FakeOpenAI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.chat = types.SimpleNamespace(completions=_FakeCompletions())

    openai_mod = types.ModuleType("openai")
    openai_mod.OpenAI = _FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", openai_mod)


def _set_credentials(monkeypatch):
    monkeypatch.setenv("WORKSPACE_URL", "https://example.databricks.com")
    monkeypatch.setenv("DATABRICKS_TOKEN", "dbx_test_dummy")


def test_empty_query(monkeypatch):
    _set_credentials(monkeypatch)
    result = json.loads(_invoke("   "))
    assert result["error"] == "empty query"
    assert result["results"] == []


def test_missing_credentials(monkeypatch):
    monkeypatch.delenv("WORKSPACE_URL", raising=False)
    monkeypatch.delenv("DATABRICKS_TOKEN", raising=False)
    result = json.loads(_invoke("coastal Japan"))
    assert "missing env var(s)" in result["error"]
    assert "WORKSPACE_URL" in result["error"]
    assert "DATABRICKS_TOKEN" in result["error"]


def test_successful_search_and_summary(monkeypatch):
    _set_credentials(monkeypatch)
    _install_fakes(monkeypatch, search_result=_SAMPLE_SEARCH, summary="  Great trip!  ")

    result = json.loads(_invoke("cities in Japan"))

    assert result["query"] == "cities in Japan"
    assert result["count"] == 2
    assert [r["title"] for r in result["results"]] == ["Kyoto", "Osaka"]
    assert result["results"][0]["content"].startswith("Kyoto is known")
    # Summary is stripped of surrounding whitespace.
    assert result["summary"] == "Great trip!"


def test_no_hits(monkeypatch):
    _set_credentials(monkeypatch)
    empty = {"manifest": {"columns": []}, "result": {"data_array": []}}
    _install_fakes(monkeypatch, search_result=empty)

    result = json.loads(_invoke("nowhere at all"))
    assert result["count"] == 0
    assert result["results"] == []
    assert result["summary"] == ""


def test_search_failure(monkeypatch):
    _set_credentials(monkeypatch)
    _install_fakes(
        monkeypatch, search_result=RuntimeError("index endpoint offline")
    )

    result = json.loads(_invoke("cities in Japan"))
    assert result["error"].startswith("city search failed:")
    assert "index endpoint offline" in result["error"]


def test_llm_failure_degrades_to_results(monkeypatch):
    _set_credentials(monkeypatch)
    _install_fakes(
        monkeypatch,
        search_result=_SAMPLE_SEARCH,
        summary=RuntimeError("serving endpoint 503"),
    )

    result = json.loads(_invoke("cities in Japan"))
    # Retrieval still succeeds even when the summary step fails.
    assert result["count"] == 2
    assert result["summary"].startswith("(summary unavailable:")
    assert "503" in result["summary"]


def test_content_truncated_to_300_chars(monkeypatch):
    _set_credentials(monkeypatch)
    long_content = "x" * 500
    search_result = {
        "manifest": {"columns": [{"name": "content"}, {"name": "title"}]},
        "result": {"data_array": [[long_content, "Longville"]]},
    }
    _install_fakes(monkeypatch, search_result=search_result)

    result = json.loads(_invoke("long place"))
    assert len(result["results"][0]["content"]) == 300
