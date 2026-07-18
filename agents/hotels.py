"""Hotel search tools backed by the LiteAPI Hotel Rates API.

LiteAPI's POST /hotels/rates supports three ways to pick hotels, each exposed
here as a separate tool:
- search_hotels_by_city         (cityName + countryCode)
- search_hotels_by_geolocation  (latitude + longitude + radius)
- search_hotels_by_location     (placeId / location identifier)

Docs: https://docs.liteapi.travel/reference/post_hotels-rates
Set LITEAPI_API_KEY in the environment (sandbox or production key).
"""

import os

import requests
from langchain_core.tools import tool

LITEAPI_RATES_URL = "https://api.liteapi.travel/v3.0/hotels/rates"
LITEAPI_HOTELS_URL = "https://api.liteapi.travel/v3.0/data/hotels"


def _fetch_hotel_ids(params: dict, api_key: str, limit: int) -> list[str]:
    """Look up hotel ids for a location via LiteAPI /data/hotels.

    Availability (rates) in the LiteAPI sandbox is only returned for explicit
    hotelIds, so filter searches resolve ids here first, then price them.
    """
    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    resp = requests.get(
        LITEAPI_HOTELS_URL,
        headers=headers,
        params={**params, "limit": limit},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json().get("data") or []
    return [h.get("id") for h in data if h.get("id")]


def _cheapest_price(entry: dict) -> tuple[str, str]:
    """Return (amount, currency) of the cheapest room offer for a hotel entry."""
    best: float | None = None
    currency = ""
    for room in entry.get("roomTypes", []):
        offer = room.get("offerRetailRate") or {}
        amount = offer.get("amount")
        if amount is None:
            # Fall back to rates[].retailRate.total[].
            for rate in room.get("rates", []):
                total = (rate.get("retailRate") or {}).get("total") or []
                if total:
                    amount = total[0].get("amount")
                    offer = {"currency": total[0].get("currency")}
                    break
        if amount is None:
            continue
        try:
            value = float(amount)
        except (TypeError, ValueError):
            continue
        if best is None or value < best:
            best = value
            currency = offer.get("currency") or currency
    if best is None:
        return "?", ""
    return f"{best:.2f}", currency


def _format_results(payload: dict, label: str) -> str:
    # LiteAPI returns HTTP 200 with an {"error": {...}} body for e.g.
    # "no availability found" (code 2001) or bad params; surface the message.
    error = payload.get("error")
    if error:
        message = (
            error.get("message", "unknown error")
            if isinstance(error, dict)
            else str(error)
        )
        return f"No hotels for {label}: {message}"

    data = payload.get("data", [])
    if not data:
        return f"No hotels found for {label}."

    # Hotel names come in a separate "hotels" array (includeHotelData / filter
    # searches); map them by id so we can show names instead of raw ids.
    names = {
        h.get("id") or h.get("hotelId"): h.get("name")
        for h in payload.get("hotels", [])
    }

    lines = []
    for entry in data[:5]:
        hotel_id = entry.get("hotelId") or entry.get("id")
        name = names.get(hotel_id) or hotel_id or "Unknown hotel"
        amount, currency = _cheapest_price(entry)
        lines.append(f"{name}: {amount} {currency}".rstrip())

    return f"{len(data)} hotels found for {label}:\n" + "\n".join(lines)


def _search_rates(
    location: dict,
    *,
    check_in: str,
    check_out: str,
    adults: int,
    rooms: int,
    currency: str,
    guest_nationality: str,
    label: str,
) -> str:
    """Call LiteAPI /hotels/rates with a location selector and shared params."""
    api_key = os.environ.get("LITEAPI_API_KEY")
    if not api_key:
        return "LITEAPI_API_KEY is not set; cannot search hotels."

    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        **location,
        "checkin": check_in,
        "checkout": check_out,
        "currency": currency,
        "guestNationality": guest_nationality,
        "occupancies": [
            {"adults": adults, "children": []} for _ in range(max(rooms, 1))
        ],
        "includeHotelData": True,
    }

    try:
        resp = requests.post(
            LITEAPI_RATES_URL, headers=headers, json=payload, timeout=30
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        return f"Hotel search failed: {exc}"

    return _format_results(resp.json(), label)


@tool
def search_hotels_by_city(
    city_name: str,
    country_code: str,
    check_in: str,
    check_out: str,
    adults: int = 2,
    rooms: int = 1,
    currency: str = "USD",
    guest_nationality: str = "US",
    limit: int = 20,
) -> str:
    """Search hotels in a city by name via LiteAPI.

    Resolves the city's hotel ids via /data/hotels, then prices them.

    Args:
        city_name: City to search, e.g. "Tokyo".
        country_code: ISO 3166-1 alpha-2 country code, e.g. "JP".
        check_in: Check-in date in YYYY-MM-DD format.
        check_out: Check-out date in YYYY-MM-DD format.
        adults: Adult guests per room (default 2).
        rooms: Number of rooms (default 1).
        currency: Display currency (default "USD").
        guest_nationality: Guest nationality ISO code (default "US").
        limit: Max hotels to look up and price (default 20).
    """
    label = f"{city_name}, {country_code}"
    api_key = os.environ.get("LITEAPI_API_KEY")
    if not api_key:
        return "LITEAPI_API_KEY is not set; cannot search hotels."

    try:
        hotel_ids = _fetch_hotel_ids(
            {"cityName": city_name, "countryCode": country_code}, api_key, limit
        )
    except requests.RequestException as exc:
        return f"Hotel search failed: {exc}"
    if not hotel_ids:
        return f"No hotels found for {label}."

    return _search_rates(
        {"hotelIds": hotel_ids},
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        rooms=rooms,
        currency=currency,
        guest_nationality=guest_nationality,
        label=label,
    )


@tool
def search_hotels_by_hotel_ids(
    hotel_ids: list[str],
    check_in: str,
    check_out: str,
    adults: int = 2,
    rooms: int = 1,
    currency: str = "USD",
    guest_nationality: str = "US",
) -> str:
    """Price a specific set of hotels by their LiteAPI hotel ids.

    Args:
        hotel_ids: LiteAPI hotel ids (from /data/hotels), e.g. ["lp2bd9f"].
        check_in: Check-in date in YYYY-MM-DD format.
        check_out: Check-out date in YYYY-MM-DD format.
        adults: Adult guests per room (default 2).
        rooms: Number of rooms (default 1).
        currency: Display currency (default "USD").
        guest_nationality: Guest nationality ISO code (default "US").
    """
    if not hotel_ids:
        return "No hotel ids provided."
    return _search_rates(
        {"hotelIds": hotel_ids},
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        rooms=rooms,
        currency=currency,
        guest_nationality=guest_nationality,
        label=f"{len(hotel_ids)} hotel id(s)",
    )


@tool
def search_hotels_by_geolocation(
    latitude: float,
    longitude: float,
    check_in: str,
    check_out: str,
    radius: int = 5000,
    adults: int = 2,
    rooms: int = 1,
    currency: str = "USD",
    guest_nationality: str = "US",
) -> str:
    """Search hotels near a coordinate via LiteAPI.

    Resolve a landmark/city to coordinates with geocode_location first.

    Args:
        latitude: Latitude of the search center, e.g. 35.6812.
        longitude: Longitude of the search center, e.g. 139.7671.
        check_in: Check-in date in YYYY-MM-DD format.
        check_out: Check-out date in YYYY-MM-DD format.
        radius: Search radius in meters (default 5000).
        adults: Adult guests per room (default 2).
        rooms: Number of rooms (default 1).
        currency: Display currency (default "USD").
        guest_nationality: Guest nationality ISO code (default "US").
    """
    return _search_rates(
        {"latitude": latitude, "longitude": longitude, "radius": radius},
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        rooms=rooms,
        currency=currency,
        guest_nationality=guest_nationality,
        label=f"({latitude}, {longitude}) r={radius}m",
    )


@tool
def search_hotels_by_location(
    place_id: str,
    check_in: str,
    check_out: str,
    adults: int = 2,
    rooms: int = 1,
    currency: str = "USD",
    guest_nationality: str = "US",
) -> str:
    """Search hotels for a LiteAPI location/place identifier.

    Args:
        place_id: LiteAPI place/region identifier (from the /data/places
            endpoint), e.g. a Google-style place id.
        check_in: Check-in date in YYYY-MM-DD format.
        check_out: Check-out date in YYYY-MM-DD format.
        adults: Adult guests per room (default 2).
        rooms: Number of rooms (default 1).
        currency: Display currency (default "USD").
        guest_nationality: Guest nationality ISO code (default "US").
    """
    return _search_rates(
        {"placeId": place_id},
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        rooms=rooms,
        currency=currency,
        guest_nationality=guest_nationality,
        label=f"place {place_id}",
    )
