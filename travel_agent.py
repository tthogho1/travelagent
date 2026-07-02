"""
Minimal AI travel-planning agent sample using LangGraph + OpenAI.

Setup:
    pip install -r requirements.txt
    setx OPENAI_API_KEY "your-api-key"

Run:
    python travel_agent.py
"""

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from agents import search_flights, search_hotels

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
