# Hugging Face Spaces (Docker SDK) image for the travel-planning agent.
FROM python:3.11-slim

WORKDIR /app

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1

# Install dependencies first so layer caching survives app-code edits.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Application code.
COPY web.py travel_agent.py agent_logging.py ./
COPY agents/ ./agents/
COPY templates/ ./templates/

# Spaces routes external traffic to port 7860 and needs 0.0.0.0 binding.
# LOG_FILE is blank because the container filesystem is ephemeral; logs go to
# stdout, which shows up in the Space's log viewer.
ENV HOST=0.0.0.0 \
    PORT=7860 \
    LOG_FILE=""

EXPOSE 7860

CMD ["python", "web.py"]
