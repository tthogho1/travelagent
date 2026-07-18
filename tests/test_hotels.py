"""Tests for the LiteAPI-backed hotel search tools.

The LiteAPI HTTP call is mocked, so these run offline and need no key.
Run with:  pytest tests/test_hotels.py -v
"""

import requests

from agents.hotels import (
    search_hotels_by_city,
    search_hotels_by_geolocation,
    search_hotels_by_hotel_ids,
    search_hotels_by_location,
)

# A representative /hotels/rates response: rate data + a hotels array (names).
_SAMPLE = {
    "data": [
        {
            "hotelId": "lp1",
            "roomTypes": [
                {"offerRetailRate": {"amount": 150.0, "currency": "USD"}},
                {"offerRetailRate": {"amount": 175.0, "currency": "USD"}},
            ],
        },
        {
            "hotelId": "lp2",
            "roomTypes": [
                {"offerRetailRate": {"amount": 90.5, "currency": "USD"}}
            ],
        },
    ],
    "hotels": [
        {"id": "lp1", "name": "Hotel Granvia"},
        {"id": "lp2", "name": "Tokyo Central Hotel"},
    ],
}


class _FakeResponse:
    def __init__(self, payload, raise_exc=None):
        self._payload = payload
        self._raise_exc = raise_exc

    def raise_for_status(self):
        if self._raise_exc is not None:
            raise self._raise_exc

    def json(self):
        return self._payload


def _mock_post(monkeypatch, payload=_SAMPLE, capture=None, raise_exc=None):
    def _post(url, headers=None, json=None, timeout=None):
        if capture is not None:
            capture["url"] = url
            capture["headers"] = headers
            capture["json"] = json
        if raise_exc is not None:
            return _FakeResponse({}, raise_exc=raise_exc)
        return _FakeResponse(payload)

    monkeypatch.setattr("agents.hotels.requests.post", _post)


def _mock_get(monkeypatch, ids=("lp1", "lp2"), capture=None, raise_exc=None):
    """Mock GET /data/hotels used by the city two-step lookup."""

    def _get(url, headers=None, params=None, timeout=None):
        if capture is not None:
            capture["url"] = url
            capture["headers"] = headers
            capture["params"] = params
        if raise_exc is not None:
            return _FakeResponse({}, raise_exc=raise_exc)
        return _FakeResponse({"data": [{"id": i} for i in ids]})

    monkeypatch.setattr("agents.hotels.requests.get", _get)


def test_missing_key(monkeypatch):
    monkeypatch.delenv("LITEAPI_API_KEY", raising=False)
    result = search_hotels_by_city.invoke(
        {
            "city_name": "Tokyo",
            "country_code": "JP",
            "check_in": "2026-08-01",
            "check_out": "2026-08-03",
        }
    )
    assert "LITEAPI_API_KEY is not set" in result


def test_city_search_formatting_and_names(monkeypatch):
    monkeypatch.setenv("LITEAPI_API_KEY", "sand_dummy")
    _mock_get(monkeypatch, ids=["lp1", "lp2"])
    _mock_post(monkeypatch)
    result = search_hotels_by_city.invoke(
        {
            "city_name": "Tokyo",
            "country_code": "JP",
            "check_in": "2026-08-01",
            "check_out": "2026-08-03",
        }
    )
    assert "2 hotels found for Tokyo, JP" in result
    # Cheapest of the two room types is shown, names resolved from `hotels`.
    assert "Hotel Granvia: 150.00 USD" in result
    assert "Tokyo Central Hotel: 90.50 USD" in result


def test_city_two_step_lookup_and_payload(monkeypatch):
    monkeypatch.setenv("LITEAPI_API_KEY", "sand_dummy")
    get_cap, post_cap = {}, {}
    _mock_get(monkeypatch, ids=["lp1", "lp2"], capture=get_cap)
    _mock_post(monkeypatch, capture=post_cap)
    search_hotels_by_city.invoke(
        {
            "city_name": "Osaka",
            "country_code": "JP",
            "check_in": "2026-08-01",
            "check_out": "2026-08-03",
            "adults": 3,
            "rooms": 2,
        }
    )
    # Step 1: /data/hotels looked up by city.
    assert get_cap["params"]["cityName"] == "Osaka"
    assert get_cap["params"]["countryCode"] == "JP"
    # Step 2: rates priced the resolved ids, not the city name.
    body = post_cap["json"]
    assert post_cap["headers"]["X-API-Key"] == "sand_dummy"
    assert body["hotelIds"] == ["lp1", "lp2"]
    assert body["includeHotelData"] is True
    assert body["occupancies"] == [
        {"adults": 3, "children": []},
        {"adults": 3, "children": []},
    ]


def test_by_hotel_ids(monkeypatch):
    monkeypatch.setenv("LITEAPI_API_KEY", "sand_dummy")
    captured = {}
    _mock_post(monkeypatch, capture=captured)
    result = search_hotels_by_hotel_ids.invoke(
        {
            "hotel_ids": ["lp1", "lp2"],
            "check_in": "2026-08-01",
            "check_out": "2026-08-03",
        }
    )
    assert captured["json"]["hotelIds"] == ["lp1", "lp2"]
    assert "2 hotels found for 2 hotel id(s)" in result


def test_by_hotel_ids_empty():
    assert search_hotels_by_hotel_ids.invoke(
        {"hotel_ids": [], "check_in": "2026-08-01", "check_out": "2026-08-03"}
    ) == "No hotel ids provided."


def test_geolocation_payload(monkeypatch):
    monkeypatch.setenv("LITEAPI_API_KEY", "sand_dummy")
    captured = {}
    _mock_post(monkeypatch, capture=captured)
    search_hotels_by_geolocation.invoke(
        {
            "latitude": 35.6812,
            "longitude": 139.7671,
            "check_in": "2026-08-01",
            "check_out": "2026-08-03",
            "radius": 1000,
        }
    )
    body = captured["json"]
    assert body["latitude"] == 35.6812
    assert body["longitude"] == 139.7671
    assert body["radius"] == 1000


def test_location_payload(monkeypatch):
    monkeypatch.setenv("LITEAPI_API_KEY", "sand_dummy")
    captured = {}
    _mock_post(monkeypatch, capture=captured)
    search_hotels_by_location.invoke(
        {
            "place_id": "ChIJ_place_123",
            "check_in": "2026-08-01",
            "check_out": "2026-08-03",
        }
    )
    assert captured["json"]["placeId"] == "ChIJ_place_123"


def test_no_hotels(monkeypatch):
    monkeypatch.setenv("LITEAPI_API_KEY", "sand_dummy")
    # No ids from /data/hotels -> short-circuit before pricing.
    _mock_get(monkeypatch, ids=[])
    result = search_hotels_by_city.invoke(
        {
            "city_name": "Nowhere",
            "country_code": "ZZ",
            "check_in": "2026-08-01",
            "check_out": "2026-08-03",
        }
    )
    assert result == "No hotels found for Nowhere, ZZ."


def test_api_error_message_surfaced(monkeypatch):
    monkeypatch.setenv("LITEAPI_API_KEY", "sand_dummy")
    _mock_get(monkeypatch, ids=["lp1"])
    # LiteAPI returns HTTP 200 with an error body for "no availability".
    _mock_post(
        monkeypatch,
        payload={"error": {"code": 2001, "message": "no availability found"}},
    )
    result = search_hotels_by_city.invoke(
        {
            "city_name": "Tokyo",
            "country_code": "JP",
            "check_in": "2026-08-01",
            "check_out": "2026-08-03",
        }
    )
    assert result == "No hotels for Tokyo, JP: no availability found"


def test_request_failure(monkeypatch):
    monkeypatch.setenv("LITEAPI_API_KEY", "sand_dummy")
    _mock_post(monkeypatch, raise_exc=requests.HTTPError("401 Unauthorized"))
    result = search_hotels_by_geolocation.invoke(
        {
            "latitude": 0.0,
            "longitude": 0.0,
            "check_in": "2026-08-01",
            "check_out": "2026-08-03",
        }
    )
    assert result.startswith("Hotel search failed:")
    assert "401" in result


def test_falls_back_to_rates_total(monkeypatch):
    monkeypatch.setenv("LITEAPI_API_KEY", "sand_dummy")
    payload = {
        "data": [
            {
                "hotelId": "lp9",
                "roomTypes": [
                    {
                        "rates": [
                            {
                                "retailRate": {
                                    "total": [{"amount": 200, "currency": "EUR"}]
                                }
                            }
                        ]
                    }
                ],
            }
        ],
        "hotels": [{"id": "lp9", "name": "Fallback Inn"}],
    }
    _mock_get(monkeypatch, ids=["lp9"])
    _mock_post(monkeypatch, payload=payload)
    result = search_hotels_by_city.invoke(
        {
            "city_name": "Paris",
            "country_code": "FR",
            "check_in": "2026-08-01",
            "check_out": "2026-08-03",
        }
    )
    assert "Fallback Inn: 200.00 EUR" in result


def test_result_caps_at_five(monkeypatch):
    monkeypatch.setenv("LITEAPI_API_KEY", "sand_dummy")
    payload = {
        "data": [
            {
                "hotelId": f"lp{i}",
                "roomTypes": [{"offerRetailRate": {"amount": i, "currency": "USD"}}],
            }
            for i in range(10)
        ]
    }
    _mock_get(monkeypatch, ids=[f"lp{i}" for i in range(10)])
    _mock_post(monkeypatch, payload=payload)
    result = search_hotels_by_city.invoke(
        {
            "city_name": "Big",
            "country_code": "US",
            "check_in": "2026-08-01",
            "check_out": "2026-08-03",
        }
    )
    assert "10 hotels found" in result
    assert result.count("USD") == 5
