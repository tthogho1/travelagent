"""Tests for agents.hotels.search_hotels.

The Duffel Stays HTTP call is mocked, so these run offline and need no token.
Run with:  pytest tests/test_hotels.py -v
"""

import requests

from agents.hotels import search_hotels

_TOKYO = {"latitude": 35.6812, "longitude": 139.7671}


def _invoke(**overrides):
    args = {**_TOKYO, "check_in": "2026-08-01", "check_out": "2026-08-03"}
    args.update(overrides)
    return search_hotels.invoke(args)


def _stay(name, amount, currency="USD"):
    return {
        "accommodation": {"name": name},
        "cheapest_rate_total_amount": amount,
        "cheapest_rate_currency": currency,
    }


class _FakeResponse:
    """Minimal stand-in for requests.Response."""

    def __init__(self, payload, raise_exc=None):
        self._payload = payload
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc is not None:
            raise self._raise_exc

    def json(self):
        return self._payload


def test_missing_token(monkeypatch):
    monkeypatch.delenv("DUFFEL_API_KEY", raising=False)
    monkeypatch.delenv("DUFFEL_ACCESS_TOKEN", raising=False)
    result = _invoke()
    assert "DUFFEL_API_KEY is not set" in result


def test_successful_search_formatting(monkeypatch):
    monkeypatch.setenv("DUFFEL_API_KEY", "duffel_test_dummy")
    payload = {
        "data": {
            "results": [
                _stay("Hotel Granvia", "150.00"),
                _stay("Tokyo Central Hotel", "90.00"),
            ]
        }
    }
    monkeypatch.setattr(
        "agents.hotels.requests.post",
        lambda *a, **k: _FakeResponse(payload),
    )

    result = _invoke()
    assert "2 hotels found near (35.6812, 139.7671)" in result
    assert "Hotel Granvia: 150.00 USD" in result
    assert "Tokyo Central Hotel: 90.00 USD" in result


def test_request_payload_forwarded(monkeypatch):
    monkeypatch.setenv("DUFFEL_API_KEY", "duffel_test_dummy")
    captured = {}

    def _fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _FakeResponse({"data": {"results": [_stay("H", "1")]}})

    monkeypatch.setattr("agents.hotels.requests.post", _fake_post)
    _invoke(adults=3, rooms=2, radius_km=10)

    data = captured["json"]["data"]
    assert captured["headers"]["Authorization"] == "Bearer duffel_test_dummy"
    assert data["rooms"] == 2
    assert data["location"]["radius"] == 10
    assert data["location"]["geographic_coordinates"] == {
        "latitude": 35.6812,
        "longitude": 139.7671,
    }
    assert data["check_in_date"] == "2026-08-01"
    assert data["guests"] == [{"type": "adult"}] * 3


def test_no_hotels(monkeypatch):
    monkeypatch.setenv("DUFFEL_API_KEY", "duffel_test_dummy")
    monkeypatch.setattr(
        "agents.hotels.requests.post",
        lambda *a, **k: _FakeResponse({"data": {"results": []}}),
    )

    result = _invoke()
    assert result.startswith("No hotels found near (35.6812, 139.7671)")


def test_request_failure(monkeypatch):
    monkeypatch.setenv("DUFFEL_API_KEY", "duffel_test_dummy")

    def _boom(*a, **k):
        return _FakeResponse({}, raise_exc=requests.HTTPError("401 Unauthorized"))

    monkeypatch.setattr("agents.hotels.requests.post", _boom)

    result = _invoke()
    assert result.startswith("Hotel search failed:")
    assert "401" in result


def test_result_caps_at_five(monkeypatch):
    monkeypatch.setenv("DUFFEL_API_KEY", "duffel_test_dummy")
    results = [_stay(f"Hotel {i}", str(i)) for i in range(10)]
    monkeypatch.setattr(
        "agents.hotels.requests.post",
        lambda *a, **k: _FakeResponse({"data": {"results": results}}),
    )

    result = _invoke()
    assert "10 hotels found" in result
    assert result.count("USD") == 5
