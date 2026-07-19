"""Flight search tool backed by the Duffel API."""

import os
from datetime import date as _date

import requests
from langchain_core.tools import tool

DUFFEL_BASE_URL = "https://api.duffel.com/air"


@tool
def search_flights(origin: str, destination: str, date: str) -> str:
    """Search for available flights between two airports via the Duffel API.

    Args:
        origin: Departure airport/city IATA code, e.g. "HND" or "TYO".
        destination: Arrival airport/city IATA code, e.g. "ITM" or "OSA".
        date: Travel date in YYYY-MM-DD format.
    """
    # Models have no clock and will happily invent a stale date from their
    # training data; reject past dates so the agent must correct itself.
    today = _date.today()
    try:
        travel_date = _date.fromisoformat(date)
    except ValueError:
        return (
            f"Invalid date '{date}'. Use YYYY-MM-DD format. "
            f"Today is {today.isoformat()}."
        )
    if travel_date < today:
        return (
            f"Date {date} is in the past. Today is {today.isoformat()}. "
            "Ask the user for a future travel date instead of guessing."
        )

    api_key = os.environ.get("DUFFEL_API_KEY")
    if not api_key:
        return "DUFFEL_API_KEY is not set; cannot search flights."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Duffel-Version": "v2",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
    }
    payload = {
        "data": {
            "slices": [
                {
                    "origin": origin,
                    "destination": destination,
                    "departure_date": date,
                }
            ],
            "passengers": [{"type": "adult"}],
            "cabin_class": "economy",
            "max_connections": 1,
        }
    }

    try:
        resp = requests.post(
            f"{DUFFEL_BASE_URL}/offer_requests",
            headers=headers,
            params={"return_offers": "true", "supplier_timeout": "15000"},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        return f"Flight search failed: {exc}"

    offers = resp.json().get("data", {}).get("offers", [])
    if not offers:
        return f"No flights found from {origin} to {destination} on {date}."

    lines = []
    for offer in offers[:5]:
        carrier = offer.get("owner", {}).get("name", "Unknown airline")
        amount = offer.get("total_amount", "?")
        currency = offer.get("total_currency", "")
        segments = offer.get("slices", [{}])[0].get("segments", [])
        dep = segments[0].get("departing_at", "?") if segments else "?"
        stops = max(len(segments) - 1, 0)
        lines.append(
            f"{carrier}: {amount} {currency}, departs {dep}, "
            f"{stops} stop(s)"
        )

    return (
        f"{len(offers)} flights found from {origin} to {destination} on {date}:\n"
        + "\n".join(lines)
    )
