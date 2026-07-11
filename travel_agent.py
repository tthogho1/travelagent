"""
Minimal AI travel-planning agent sample using LangGraph + OpenAI.

Setup:
    pip install -r requirements.txt
    cp .env.example .env   # then fill in your API keys

Run:
    python travel_agent.py
"""

from dotenv import load_dotenv

# Load environment variables from a local .env file before anything below
# reads OPENAI_API_KEY / DUFFEL_API_KEY.
load_dotenv()

from langchain.agents import create_agent  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402

from agent_logging import AgentLogger, configure_logging, logger  # noqa: E402
from agents import (  # noqa: E402
    geocode_location,
    search_cities,
    search_flights,
    search_hotels,
)

configure_logging()

model = ChatOpenAI(model="gpt-4o", max_tokens=2000)

agent = create_agent(
    model,
    tools=[search_cities, geocode_location, search_flights], #search_hotels],
    system_prompt=(
        "You are a helpful travel-planning assistant. Use the available tools "
        "to help the user plan their trip: search_cities to discover "
        "destinations, geocode_location to resolve landmarks/cities to "
        "coordinates, and the flight search tool to find options. "
        "Then summarize the best options."
    ),
)


def ask(user_message: str) -> str:
    """Run the agent and return the assistant's final reply as text."""
    logger.info("USER ▶ %s", user_message)
    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_message}]},
        config={"callbacks": [AgentLogger()]},
    )
    final = result["messages"][-1].content
    # Some models return content as a list of parts; join to plain text.
    if isinstance(final, list):
        final = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in final
        )
    logger.info("AGENT ◀ %s", final)
    return final


def run(user_message: str) -> None:
    print(ask(user_message))


if __name__ == "__main__":
    run("Plan a trip from Tokyo to Osaka on 2026-08-10, returning 2026-08-13.")
