"""Talks to Gemma. Where Gemma runs depends on AI_MODE:

  local  Gemma runs on this machine, through Ollama.
  cloud  Gemma 4 runs at Google, through the Gemini API's free tier.
         (Used on small free servers that can't hold a model.)

Either way it is the same open-weight model family, the same prompts, and
the same code checks afterwards (see extract.py and verify.py)."""

import asyncio
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

# One question at a time: two at once on a CPU just make both slower, and
# on the free cloud tier it keeps us inside the rate limit.
_one_at_a_time = asyncio.Lock()

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"
# The free tier allows a limited number of requests per minute. Leaving this
# gap between calls keeps us under it even when several players report at once.
CLOUD_GAP_SECONDS = 4.5
# "Too many requests" or a server hiccup: wait this long, then try again.
CLOUD_RETRY_WAITS = (5, 20)
_last_cloud_call = 0.0


def is_cloud() -> bool:
    return settings.ai_mode == "cloud"


async def chat(system: str, user: str, *, json_mode: bool = False,
               temperature: float = 0.1, max_tokens: int | None = None) -> str:
    """Send one question to Gemma and return its answer as text."""
    async with _one_at_a_time:
        started = time.perf_counter()
        if is_cloud():
            answer = await _ask_gemini(system, user, json_mode, temperature, max_tokens)
        else:
            answer = await _ask_ollama(system, user, json_mode, temperature, max_tokens)
    log.info("Gemma (%s) answered in %.1f s (%d characters)",
             settings.ai_mode, time.perf_counter() - started, len(answer))
    return answer


async def chat_json(system: str, user: str) -> dict:
    """Like chat(), but the answer must be a JSON object. Retries once."""
    for attempt in (1, 2):
        answer = await chat(system, user, json_mode=True)
        try:
            data = json.loads(_strip_code_fence(answer))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
        log.warning("Gemma's answer was not a JSON object (attempt %d)", attempt)
    raise ValueError("Gemma did not return valid JSON.")


def _strip_code_fence(text: str) -> str:
    """Models sometimes wrap JSON in ```json ... ``` marks. Take them off."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    return text.strip()


# --- local: Ollama ---------------------------------------------------------

def _keep_alive():
    """Ollama wants a time like "30m", or a plain number: -1 means "forever"."""
    value = settings.ollama_keep_alive.strip()
    return int(value) if value.lstrip("-").isdigit() else value


async def _ask_ollama(system, user, json_mode, temperature, max_tokens) -> str:
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

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(f"{settings.ollama_url}/api/chat", json=payload)
        response.raise_for_status()
    return response.json()["message"]["content"]


# --- cloud: Gemma 4 on the Gemini API ---------------------------------------

async def _ask_gemini(system, user, json_mode, temperature, max_tokens) -> str:
    global _last_cloud_call
    if not settings.gemini_api_key:
        raise RuntimeError("AI_MODE is cloud but GEMINI_API_KEY is not set.")

    config = {"temperature": temperature,
              # Gemma 4 "thinks" before answering unless told to keep it minimal.
              # Our tasks are small, and thinking makes every answer much slower.
              "thinkingConfig": {"thinkingLevel": "minimal"}}
    if json_mode:
        config["responseMimeType"] = "application/json"
    if max_tokens:
        config["maxOutputTokens"] = max_tokens
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": config,
    }
    url = f"{GEMINI_URL}/{settings.gemini_model}:generateContent"
    # The key goes in a header, not in the address, so it can't end up in a log.
    headers = {"x-goog-api-key": settings.gemini_api_key}

    for wait in (*CLOUD_RETRY_WAITS, None):
        # Keep a gap since the last call (the free tier's per-minute limit).
        gap = CLOUD_GAP_SECONDS - (time.monotonic() - _last_cloud_call)
        if gap > 0:
            await asyncio.sleep(gap)
        _last_cloud_call = time.monotonic()

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, headers=headers, json=body)
        if response.status_code == 200:
            return _gemini_text(response.json())
        if response.status_code == 400 and "thinkingConfig" in config:
            # This model doesn't take the thinking setting: ask again without it.
            del config["thinkingConfig"]
            continue
        # 429 = too many requests; 5xx = Google's side. Both are worth another try.
        if response.status_code in (429, 500, 502, 503, 504) and wait is not None:
            log.warning("Gemini API answered %d; trying again in %d s", response.status_code, wait)
            await asyncio.sleep(wait)
            continue
        raise RuntimeError(f"Gemini API error {response.status_code}")
    raise RuntimeError("Gemini API kept failing.")


def _gemini_text(data: dict) -> str:
    """The answer's text, leaving out any "thought" parts."""
    candidates = data.get("candidates") or []
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(part.get("text", "") for part in parts if not part.get("thought")).strip()


# --- warm-up (only matters for the local model) -----------------------------

async def warm_up(system: str) -> None:
    """Load Gemma and let it read a system prompt, so the first real voice note
    doesn't pay for that. Run in the background when the server starts."""
    if is_cloud():
        return  # nothing to load: the model is already running at Google
    try:
        await chat(system, "Player said: \"hello\"", max_tokens=1)
        log.info("Gemma is warmed up.")
    except Exception as error:
        log.warning("Could not warm up Gemma (is Ollama running?): %s", type(error).__name__)


async def model_loaded() -> bool:
    """Is Gemma ready to answer quickly? (If not, the next answer takes much longer.)"""
    if is_cloud():
        return True
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            running = (await client.get(f"{settings.ollama_url}/api/ps")).json()
        return any(m.get("name") == settings.ollama_model for m in running.get("models", []))
    except Exception:
        return False
