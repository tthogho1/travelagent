"""Tests for agents.flights.search_flights.

The Duffel HTTP call is mocked, so these run offline and need no API key.
Run with:  pytest tests/test_flights.py -v
"""

import requests

from agents.flights import search_flights


def _invoke(origin="HND", destination="ITM", date="2026-08-10"):
    """Call the LangChain tool the way an agent would."""
    return search_flights.invoke(
        {"origin": origin, "destination": destination, "date": date}
    )


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


def test_missing_api_key(monkeypatch):
    monkeypatch.delenv("DUFFEL_API_KEY", raising=False)
    result = _invoke()
    assert "DUFFEL_API_KEY is not set" in result


def test_successful_search_formatting(monkeypatch):
    monkeypatch.setenv("DUFFEL_API_KEY", "duffel_test_dummy")
    payload = {
        "data": {
            "offers": [
                {
                    "owner": {"name": "JAL"},
                    "total_amount": "85.20",
                    "total_currency": "USD",
                    "slices": [
                        {
                            "segments": [
                                {"departing_at": "2026-08-10T18:00:00"},
                            ]
                        }
                    ],
                },
                {
                    "owner": {"name": "ANA"},
                    "total_amount": "120.00",
                    "total_currency": "USD",
                    "slices": [
                        {
                            "segments": [
                                {"departing_at": "2026-08-10T06:00:00"},
                                {"departing_at": "2026-08-10T09:00:00"},
                            ]
                        }
                    ],
                },
            ]
        }
    }
    monkeypatch.setattr(
        "agents.flights.requests.post",
        lambda *a, **k: _FakeResponse(payload),
    )

    result = _invoke("HND", "ITM", "2026-08-10")

    assert "2 flights found from HND to ITM on 2026-08-10" in result
    assert "JAL: 85.20 USD, departs 2026-08-10T18:00:00, 0 stop(s)" in result
    # Two segments -> one connection -> 1 stop.
    assert "ANA: 120.00 USD, departs 2026-08-10T06:00:00, 1 stop(s)" in result


def test_no_offers(monkeypatch):
    monkeypatch.setenv("DUFFEL_API_KEY", "duffel_test_dummy")
    monkeypatch.setattr(
        "agents.flights.requests.post",
        lambda *a, **k: _FakeResponse({"data": {"offers": []}}),
    )

    result = _invoke("HND", "ITM", "2026-08-10")
    assert result == "No flights found from HND to ITM on 2026-08-10."


def test_request_failure(monkeypatch):
    monkeypatch.setenv("DUFFEL_API_KEY", "duffel_test_dummy")

    def _boom(*a, **k):
        return _FakeResponse(
            {}, raise_exc=requests.HTTPError("422 Unprocessable Entity")
        )

    monkeypatch.setattr("agents.flights.requests.post", _boom)

    result = _invoke("ZZZ", "YYY", "2026-08-10")
    assert result.startswith("Flight search failed:")
    assert "422" in result


def test_result_caps_at_five_lines(monkeypatch):
    monkeypatch.setenv("DUFFEL_API_KEY", "duffel_test_dummy")
    offers = [
        {
            "owner": {"name": f"Airline{i}"},
            "total_amount": str(i),
            "total_currency": "USD",
            "slices": [{"segments": [{"departing_at": "2026-08-10T00:00:00"}]}],
        }
        for i in range(10)
    ]
    monkeypatch.setattr(
        "agents.flights.requests.post",
        lambda *a, **k: _FakeResponse({"data": {"offers": offers}}),
    )

    result = _invoke()
    # Header reports the true total, but only 5 detail lines are shown.
    assert "10 flights found" in result
    assert result.count("USD") == 5
