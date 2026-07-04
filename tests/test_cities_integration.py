"""Integration test that runs the REAL RAG pipeline for search_cities.

Unlike tests/test_cities.py (which mocks Databricks + the LLM), this test
actually calls the Databricks Vector Search index and the serving-endpoint LLM.
It is skipped unless real credentials are present, so the normal offline suite
is unaffected.

Enable it by setting credentials (e.g. in .env) and opting in:

    RUN_CITIES_INTEGRATION=1 ./venv/bin/python -m pytest \
        tests/test_cities_integration.py -v -s
"""

import json
import os

import pytest
from dotenv import load_dotenv

from agents.cities import search_cities

# Pull WORKSPACE_URL / DATABRICKS_TOKEN from a local .env if present.
load_dotenv()

_HAS_CREDS = bool(os.environ.get("WORKSPACE_URL") and os.environ.get("DATABRICKS_TOKEN"))
_OPTED_IN = os.environ.get("RUN_CITIES_INTEGRATION") == "1"

pytestmark = pytest.mark.skipif(
    not (_HAS_CREDS and _OPTED_IN),
    reason=(
        "Live RAG test: set WORKSPACE_URL, DATABRICKS_TOKEN and "
        "RUN_CITIES_INTEGRATION=1 to run."
    ),
)


def test_real_rag_answers_query():
    raw = search_cities.invoke({"query": "best places to visit in Japan"})
    payload = json.loads(raw)

    # A real run should not surface any of the guard/error branches.
    assert "error" not in payload, payload.get("error")

    assert payload["count"] >= 1
    assert payload["results"], "expected at least one retrieved passage"
    for item in payload["results"]:
        assert item["title"]
        assert item["content"]

    # The LLM summary step should have produced real text, not the degraded
    # "(summary unavailable: ...)" fallback.
    summary = payload["summary"]
    assert summary
    assert not summary.startswith("(summary unavailable:"), summary

    # Print so `-s` shows what the RAG pipeline actually returned.
    print("\nSummary:", summary)
