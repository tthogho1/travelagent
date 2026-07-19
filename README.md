---
title: Travel Planning Agent
emoji: ✈️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# ✈️ Travel Planning Agent

A travel-planning agent built with LangGraph + OpenAI. Chat about destinations,
flights, and hotels, and show landmarks on a map.

## Features

- **Destination search** — RAG suggestions from Databricks Vector Search (Wikivoyage)
- **Flight search** — Duffel API
- **Hotel search** — LiteAPI (by city, coordinates, placeId, or hotel ids)
- **Geocoding + map** — OpenStreetMap Nominatim + Leaflet
- **Conversation memory** — history kept per session

## Running locally

```bash
pip install -r requirements.txt
cp .env.example .env    # then fill in your API keys
python web.py           # -> http://127.0.0.1:8000
```

## Environment variables

| Variable | Purpose | Required |
|---|---|---|
| `OPENAI_API_KEY` | The agent model | ✅ |
| `OPENAI_MODEL` | Model id (default `o3`) | |
| `DUFFEL_API_KEY` | Flight search | |
| `LITEAPI_API_KEY` | Hotel search | |
| `WORKSPACE_URL` / `DATABRICKS_TOKEN` | Destination search (RAG) | |

See [README_HUGGINGFACE.md](README_HUGGINGFACE.md) for Hugging Face Spaces
deployment instructions.
