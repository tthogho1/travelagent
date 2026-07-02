"""
Minimal AI travel-planning agent sample using LangGraph + OpenAI.

Setup:
    pip install -r requirements.txt
    setx OPENAI_API_KEY "your-api-key"

Run:
    python travel_agent.py
"""

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent


@tool
def search_flights(origin: str, destination: str, date: str) -> str:
    """Search for available flights between two cities.

    Args:
        origin: Departure city, e.g. "Tokyo".
        destination: Arrival city, e.g. "Osaka".
        date: Travel date in YYYY-MM-DD format.
    """
    # Mocked data — replace with a real flights API call.
    return (
        f"2 flights found from {origin} to {destination} on {date}: "
        f"ANA 123 departs 08:00 ($120), JAL 456 departs 14:30 ($95)."
    )


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


model = ChatOpenAI(model="gpt-4o", max_tokens=2000)

agent = create_react_agent(
    model,
    tools=[search_flights, search_hotels],
    prompt=(
        "You are a helpful travel-planning assistant. Use the flight and "
        "hotel search tools to help the user plan their trip, then summarize "
        "the best options."
    ),
)


def run(user_message: str) -> None:
    result = agent.invoke({"messages": [{"role": "user", "content": user_message}]})
    result["messages"][-1].pretty_print()


if __name__ == "__main__":
    run("Plan a trip from Tokyo to Osaka on 2026-08-10, returning 2026-08-13.")
