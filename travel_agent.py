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

from langchain_openai import ChatOpenAI  # noqa: E402
from langgraph.prebuilt import create_react_agent  # noqa: E402

from agents import search_flights, search_hotels  # noqa: E402

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
