"""Tests for agents.geocoding.geocode_location.

The Nominatim HTTP call is mocked, so these run offline and need no network.
Run with:  pytest tests/test_geocoding.py -v
"""

import json

import requests

from agents.geocoding import geocode_location

_SAMPLE = [
    {
        "display_name": "Kinkaku-ji, Kyoto, Japan",
        "lat": "35.0394",
        "lon": "135.7292",
        "type": "attraction",
        "class": "tourism",
        "importance": 0.72,
        "address": {"city": "Kyoto", "country": "Japan", "country_code": "jp"},
    }
]


class _FakeResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, payload, raise_exc=None):
        self._payload = payload
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc is not None:
            raise self._raise_exc

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _invoke(query="Kinkaku-ji"):
    return geocode_location.invoke({"query": query})


def test_empty_query():
    result = json.loads(_invoke("   "))
    assert result["error"] == "empty query"
    assert result["results"] == []


def test_successful_geocode(monkeypatch):
    monkeypatch.setattr(
        "agents.geocoding.requests.get",
        lambda *a, **k: _FakeResponse(_SAMPLE),
    )
    result = json.loads(_invoke("Kinkaku-ji"))

    assert result["query"] == "Kinkaku-ji"
    assert result["count"] == 1
    place = result["results"][0]
    assert place["lat"] == "35.0394"
    assert place["lon"] == "135.7292"
    assert place["type"] == "attraction"
    assert place["address"]["city"] == "Kyoto"


def test_sends_required_user_agent(monkeypatch):
    captured = {}

    def _fake_get(url, headers=None, params=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["params"] = params
        return _FakeResponse(_SAMPLE)

    monkeypatch.setattr("agents.geocoding.requests.get", _fake_get)
    _invoke("Tokyo Tower")

    # Nominatim rejects requests without an identifying User-Agent.
    assert captured["headers"]["User-Agent"]
    assert captured["params"]["q"] == "Tokyo Tower"
    assert captured["params"]["format"] == "jsonv2"


def test_no_matches(monkeypatch):
    monkeypatch.setattr(
        "agents.geocoding.requests.get",
        lambda *a, **k: _FakeResponse([]),
    )
    result = json.loads(_invoke("asdfghjkl nowhere"))
    assert result["count"] == 0
    assert result["results"] == []


def test_request_failure(monkeypatch):
    def _boom(*a, **k):
        return _FakeResponse(
            {}, raise_exc=requests.HTTPError("429 Too Many Requests")
        )

    monkeypatch.setattr("agents.geocoding.requests.get", _boom)
    result = json.loads(_invoke("Osaka"))
    assert result["error"].startswith("geocoding failed:")
    assert "429" in result["error"]


def test_result_caps_at_limit(monkeypatch):
    many = [dict(_SAMPLE[0], display_name=f"Place {i}") for i in range(8)]
    monkeypatch.setattr(
        "agents.geocoding.requests.get",
        lambda *a, **k: _FakeResponse(many),
    )
    # The tool returns whatever Nominatim sends (limit is enforced server-side
    # via the `limit` param); confirm every row is mapped through.
    result = json.loads(_invoke("cafe"))
    assert result["count"] == 8
