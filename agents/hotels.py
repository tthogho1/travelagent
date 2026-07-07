"""Hotel search tool backed by the Duffel Stays API.

The official duffel-api Python SDK does not cover Stays, so this calls the
Duffel Stays HTTP API directly (mirroring the flight tool). Stays searches by
coordinate, so resolve a city/landmark to a latitude/longitude first — e.g.
with geocode_location — then call this tool.
"""

import os

import requests
from langchain_core.tools import tool

DUFFEL_STAYS_URL = "https://api.duffel.com/stays/search"


@tool
def search_hotels(
    latitude: float,
    longitude: float,
    check_in: str,
    check_out: str,
    adults: int = 2,
    rooms: int = 1,
    radius_km: int = 5,
) -> str:
    """Search for available hotels near a coordinate via the Duffel Stays API.

    Resolve a city/landmark to coordinates with geocode_location first, then
    pass the latitude/longitude here.

    Args:
        latitude: Latitude of the search center, e.g. 35.6812 (Tokyo Station).
        longitude: Longitude of the search center, e.g. 139.7671.
        check_in: Check-in date in YYYY-MM-DD format.
        check_out: Check-out date in YYYY-MM-DD format.
        adults: Number of adult guests (default 2).
        rooms: Number of rooms (default 1).
        radius_km: Search radius in kilometers (default 5).
    """
    api_key = os.environ.get("DUFFEL_API_KEY") or os.environ.get(
        "DUFFEL_ACCESS_TOKEN"
    )
    if not api_key:
        return "DUFFEL_API_KEY is not set; cannot search hotels."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Duffel-Version": "v2",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "data": {
            "rooms": rooms,
            "location": {
                "radius": radius_km,
                "geographic_coordinates": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
            },
            "check_in_date": check_in,
            "check_out_date": check_out,
            "guests": [{"type": "adult"} for _ in range(adults)],
        }
    }

    try:
        resp = requests.post(
            DUFFEL_STAYS_URL, headers=headers, json=payload, timeout=30
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        return f"Hotel search failed: {exc}"

    results = resp.json().get("data", {}).get("results", [])
    if not results:
        return (
            f"No hotels found near ({latitude}, {longitude}) "
            f"from {check_in} to {check_out}."
        )

    lines = []
    for stay in results[:5]:
        name = stay.get("accommodation", {}).get("name", "Unknown hotel")
        amount = stay.get("cheapest_rate_total_amount", "?")
        currency = stay.get("cheapest_rate_currency", "")
        lines.append(f"{name}: {amount} {currency}".rstrip())

    return (
        f"{len(results)} hotels found near ({latitude}, {longitude}) "
        f"from {check_in} to {check_out}:\n" + "\n".join(lines)
    )
