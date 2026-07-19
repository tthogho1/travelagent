"""Web server for the travel-planning agent.

Serves a small chat UI and exposes a /chat endpoint that runs the LangChain
agent defined in travel_agent.py.

Run:
    pip install -r requirements.txt
    cp .env.example .env          # then set OPENAI_API_KEY (+ DUFFEL_API_KEY)
    python web.py                 # -> http://127.0.0.1:8000

Or with uvicorn directly:
    uvicorn web:app --reload
"""

import json
import os
import uuid
from pathlib import Path

from fastapi import Cookie, FastAPI, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agents import geocode_location
from travel_agent import ask

app = FastAPI(title="Travel Planning Agent")

INDEX_HTML = Path(__file__).parent / "templates" / "index.html"
SESSION_COOKIE = "session_id"


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    response: Response,
    session_id: str | None = Cookie(default=None),
) -> ChatResponse:
    # Give each browser a stable session id so the agent recalls the
    # conversation history for follow-up questions.
    if not session_id:
        session_id = uuid.uuid4().hex
        response.set_cookie(
            SESSION_COOKIE, session_id, httponly=True, samesite="lax"
        )

    message = (req.message or "").strip()
    if not message:
        return ChatResponse(reply="Please enter a request.")
    try:
        reply = ask(message, session_id=session_id)
    except Exception as exc:  # noqa: BLE001 — surface errors to the UI
        reply = f"Error: {exc}"
    return ChatResponse(reply=reply)


@app.post("/reset")
def reset(response: Response) -> dict:
    """Start a new conversation by clearing the session cookie."""
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@app.get("/geocode")
def geocode(q: str) -> dict:
    """Resolve a landmark/city name to coordinates for the map.

    Proxies OpenStreetMap Nominatim through the existing geocode_location
    tool, which sets the User-Agent that Nominatim's usage policy requires
    (a browser cannot set it, so we must not call Nominatim from the client).
    """
    q = (q or "").strip()
    if not q:
        return {"error": "empty query"}

    payload = json.loads(geocode_location.invoke({"query": q}))
    if payload.get("error"):
        return {"error": payload["error"]}

    results = payload.get("results", [])
    if not results:
        return {"error": f"'{q}' not found"}

    best = results[0]
    return {
        "lat": float(best["lat"]),
        "lon": float(best["lon"]),
        "display_name": best.get("display_name", q),
    }


@app.get("/", response_class=FileResponse)
def index() -> FileResponse:
    return FileResponse(INDEX_HTML)


if __name__ == "__main__":
    import uvicorn

    # Defaults suit local dev; containers (e.g. Hugging Face Spaces) override
    # with HOST=0.0.0.0 and PORT=7860.
    uvicorn.run(
        app,
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
    )
