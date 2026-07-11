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

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from travel_agent import ask

app = FastAPI(title="Travel Planning Agent")

INDEX_HTML = Path(__file__).parent / "templates" / "index.html"


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    message = (req.message or "").strip()
    if not message:
        return ChatResponse(reply="Please enter a request.")
    try:
        reply = ask(message)
    except Exception as exc:  # noqa: BLE001 — surface errors to the UI
        reply = f"Error: {exc}"
    return ChatResponse(reply=reply)


@app.get("/", response_class=FileResponse)
def index() -> FileResponse:
    return FileResponse(INDEX_HTML)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
