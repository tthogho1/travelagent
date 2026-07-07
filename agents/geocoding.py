"""Geocoding tool backed by OpenStreetMap Nominatim.

Forward-geocodes a landmark or city name into coordinates plus structured
address components. Uses the public Nominatim endpoint, which requires a
descriptive User-Agent and allows at most ~1 request/second.
See https://operations.osmfoundation.org/policies/nominatim/ for usage policy.
"""

import json
import os

import requests
from langchain_core.tools import tool

# ── Config (overridable via environment variables) ───────────────────────────
NOMINATIM_URL = os.environ.get(
    "NOMINATIM_URL", "https://nominatim.openstreetmap.org/search"
)
# Nominatim requires a valid, identifying User-Agent (app name + contact).
USER_AGENT = os.environ.get(
    "NOMINATIM_USER_AGENT", "travelagent-geocoder/1.0 (tthogho1@gmail.com)"
)
NUM_RESULTS = int(os.environ.get("GEOCODING_NUM_RESULTS", "5"))


@tool
def geocode_location(query: str) -> str:
    """Geocode a landmark or city name into coordinates and address details.

    Forward-geocodes free text (a landmark, attraction, or city name) via
    OpenStreetMap Nominatim and returns the best matching places.

    Args:
        query: Place to geocode, e.g. "Kinkaku-ji", "Tokyo Tower", or "Osaka".

    Returns:
        A JSON string with the query and a list of results, each containing
        display_name, lat, lon, type, class, importance, and address parts.
    """
    if not query or not query.strip():
        return json.dumps({"query": query, "error": "empty query", "results": []})

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    params = {
        "q": query,
        "format": "jsonv2",
        "addressdetails": 1,
        "limit": NUM_RESULTS,
    }

    try:
        resp = requests.get(
            NOMINATIM_URL, headers=headers, params=params, timeout=30
        )
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as exc:
        return json.dumps(
            {"query": query, "error": f"geocoding failed: {exc}", "results": []}
        )
    except ValueError as exc:  # invalid/empty JSON body
        return json.dumps(
            {"query": query, "error": f"invalid response: {exc}", "results": []}
        )

    results = []
    for place in payload:
        results.append(
            {
                "display_name": place.get("display_name"),
                "lat": place.get("lat"),
                "lon": place.get("lon"),
                "type": place.get("type"),
                "class": place.get("class"),
                "importance": place.get("importance"),
                "address": place.get("address", {}),
            }
        )

    return json.dumps(
        {
            "query": query,
            "count": len(results),
            "results": results,
        }
    )
