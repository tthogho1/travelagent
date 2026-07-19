# 🤗 Deploying to Hugging Face Spaces

This FastAPI app runs as a **Docker SDK** Space.

## ⚠️ Read this first: make the Space private

If the Space is **public, anyone can spend your API credits**. The app defaults
to `o3` (an expensive reasoning model), so a public Space can run up a large
bill quickly.

- **Use a private Space** (recommended)
- If you must make it public, lower the model (e.g. `OPENAI_MODEL=gpt-4o-mini`)
  and set spending limits in your OpenAI account

## 1. Create the Space

Go to [huggingface.co/spaces](https://huggingface.co/spaces) → **Create new Space**

| Setting | Value |
|---|---|
| Space SDK | **Docker** (important) |
| Hardware | CPU basic (free) is enough |
| Visibility | **Private** (recommended) |

The app loads no ML models, so it runs comfortably on the free CPU tier.

## 2. Add secrets

Under the Space's **Settings → Variables and secrets**, add the following.
`.env` is never committed, so these settings are required.

| Name | Kind | Required |
|---|---|---|
| `OPENAI_API_KEY` | Secret | ✅ |
| `OPENAI_MODEL` | Variable (e.g. `gpt-4o-mini`) | |
| `DUFFEL_API_KEY` | Secret | for flight search |
| `LITEAPI_API_KEY` | Secret | for hotel search |
| `WORKSPACE_URL` | Variable | for destination search |
| `DATABRICKS_TOKEN` | Secret | for destination search |
| `NOMINATIM_USER_AGENT` | Variable (include a contact) | recommended for the map |

> Watch for typos in variable names (e.g. a missing leading `L` in
> `LITEAPI_API_KEY`). If a key cannot be read, only that tool fails — quietly.

## 3. Push the code

Add the Space's Git repository as a remote and push.

```bash
git remote add space https://huggingface.co/spaces/<username>/<space-name>
git push space qa:main      # Spaces builds from the main branch
```

The build starts automatically and takes a few minutes. Watch it in the
Space's **Logs** tab.

## How it works (already configured)

- [Dockerfile](Dockerfile) starts the app with `python web.py`
- Spaces routes traffic to **port 7860**, so `HOST=0.0.0.0` and `PORT=7860`
  are set as environment variables ([web.py](web.py) reads them)
- The YAML frontmatter in [README.md](README.md) (`sdk: docker`,
  `app_port: 7860`) configures the Space
- `LOG_FILE=""` disables file logging; logs go to stdout and appear in the
  Space's Logs tab

## Known limitations

| Item | Details |
|---|---|
| **Conversation memory is lost** | It uses `InMemorySaver`, so history is cleared when the Space sleeps or restarts. Persisting it needs a SQLite checkpointer plus Persistent Storage (paid) |
| **Nominatim rate limits** | Spaces share IP addresses, so map geocoding may return 429. For heavy use, add caching or self-host Nominatim |
| **Sleeping** | Free Spaces sleep after a period of inactivity, adding a cold start on the next visit |
| **Ephemeral logs** | The container filesystem is wiped on restart |

## Testing the container locally

You can verify the build before pushing.

```bash
docker build -t travelagent .
docker run --rm -p 7860:7860 --env-file .env travelagent
# -> http://127.0.0.1:7860
```
