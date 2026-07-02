"""Hotel search tool."""

from langchain_core.tools import tool


@tool
def search_hotels(city: str, checkin: str, checkout: str) -> str:
    """Search for available hotels in a city for a date range.

    Args:
        city: City to search in, e.g. "Osaka".
        checkin: Check-in date in YYYY-MM-DD format.
        checkout: Check-out date in YYYY-MM-DD format.
    """
    # Mocked data — replace with a real hotels API call.
    return (
        f"2 hotels found in {city} from {checkin} to {checkout}: "
        f"Hotel Granvia ($150/night), Osaka Central Hotel ($90/night)."
    )
