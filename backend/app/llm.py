"""Talks to Gemma through Ollama, which runs on this same machine."""

import json
import logging
import time

import httpx

from .config import settings

log = logging.getLogger("starboy.llm")

# Gemma on a CPU is slow. The first call after a start is much slower still,
# because the model (about 4 GB) is first read from disk into memory.
TIMEOUT_SECONDS = 180
COLD_TIMEOUT_SECONDS = 600


def _keep_alive():
    """Ollama wants a time like "30m", or a plain number: -1 means "forever"."""
    value = settings.ollama_keep_alive.strip()
    return int(value) if value.lstrip("-").isdigit() else value


async def chat(system: str, user: str, *, json_mode: bool = False,
               temperature: float = 0.1, max_tokens: int | None = None) -> str:
    """Send one question to Gemma and return its answer as text."""
    timeout = TIMEOUT_SECONDS if await model_loaded() else COLD_TIMEOUT_SECONDS
    payload = {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "think": False,  # Gemma 4 gives empty answers with thinking on
        "keep_alive": _keep_alive(),  # keep the model in memory between voice notes
        "options": {"temperature": temperature, "num_ctx": 4096},
    }
    if json_mode:
        payload["format"] = "json"
    if max_tokens:
        payload["options"]["num_predict"] = max_tokens

    started = time.perf_counter()
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(f"{settings.ollama_url}/api/chat", json=payload)
        response.raise_for_status()
    answer = response.json()["message"]["content"]
    log.info("Gemma answered in %.1f s (%d characters)",
             time.perf_counter() - started, len(answer))
    return answer


async def chat_json(system: str, user: str) -> dict:
    """Like chat(), but the answer must be a JSON object. Retries once."""
    for attempt in (1, 2):
        answer = await chat(system, user, json_mode=True)
        try:
            data = json.loads(answer)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
        log.warning("Gemma's answer was not a JSON object (attempt %d)", attempt)
    raise ValueError("Gemma did not return valid JSON.")


async def warm_up(system: str) -> None:
    """Load Gemma and let it read a system prompt, so the first real voice note
    doesn't pay for that. Run in the background when the server starts."""
    try:
        await chat(system, "Player said: \"hello\"", max_tokens=1)
        log.info("Gemma is warmed up.")
    except Exception as error:
        log.warning("Could not warm up Gemma (is Ollama running?): %s", type(error).__name__)


async def model_loaded() -> bool:
    """Is Gemma already in memory? (If not, the next answer takes much longer.)"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            running = (await client.get(f"{settings.ollama_url}/api/ps")).json()
        return any(m.get("name") == settings.ollama_model for m in running.get("models", []))
    except Exception:
        return False
