"""Logging for agent runs.

Provides:
- configure_logging(): set up console + file logging (level/file via env vars).
- AgentLogger: a LangChain callback handler that logs every LLM and tool call.

Attach AgentLogger to an agent run via
    agent.invoke(..., config={"callbacks": [AgentLogger()]})
"""

import logging
import os
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger("travelagent")

_configured = False


def configure_logging() -> logging.Logger:
    """Configure the `travelagent` logger once (console + optional file).

    Env vars:
        LOG_LEVEL: logging level name (default "INFO").
        LOG_FILE:  path to a log file (default "agent.log"; empty to disable).
    """
    global _configured
    if _configured:
        return logger

    level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    logger.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)-5s %(name)s: %(message)s", "%H:%M:%S"
    )

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    log_file = os.environ.get("LOG_FILE", "agent.log")
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    logger.propagate = False
    _configured = True
    return logger


def _truncate(text: Any, limit: int = 500) -> str:
    text = str(text)
    return text if len(text) <= limit else text[:limit] + "…"


class AgentLogger(BaseCallbackHandler):
    """Logs LLM and tool activity during an agent run."""

    def on_chat_model_start(self, serialized, messages, **kwargs: Any) -> None:
        model = (serialized or {}).get("name", "chat_model")
        turns = sum(len(m) for m in messages)
        logger.info("LLM ▶ %s (%d message(s))", model, turns)

    def on_llm_end(self, response, **kwargs: Any) -> None:
        try:
            usage = response.llm_output.get("token_usage", {})  # type: ignore[union-attr]
        except AttributeError:
            usage = {}
        if usage:
            logger.info("LLM ◀ done (tokens: %s)", usage.get("total_tokens", "?"))
        else:
            logger.info("LLM ◀ done")

    def on_tool_start(self, serialized, input_str, **kwargs: Any) -> None:
        name = (serialized or {}).get("name", "tool")
        logger.info("TOOL ▶ %s  input=%s", name, _truncate(input_str))

    def on_tool_end(self, output, **kwargs: Any) -> None:
        logger.info("TOOL ◀ output=%s", _truncate(output))

    def on_tool_error(self, error, **kwargs: Any) -> None:
        logger.error("TOOL ✗ %s: %s", type(error).__name__, error)
