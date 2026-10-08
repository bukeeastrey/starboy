"""Voice note -> text, with Whisper. Where Whisper runs depends on AI_MODE:

  local  faster-whisper on this machine's CPU.
  cloud  Whisper large-v3 at Groq (free tier). The audio is sent there to be
         transcribed; Star Boy itself still deletes its copy straight after.
"""

import asyncio
import logging
import time
from pathlib import Path

import httpx

from .config import settings
from .prompts import WHISPER_WORDS

log = logging.getLogger("starboy.speech")

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

_model = None  # the local model, loaded the first time a voice note arrives


def is_cloud() -> bool:
    return settings.ai_mode == "cloud"


def is_loaded() -> bool:
    """Can a voice note be transcribed without first loading a model?"""
    return is_cloud() or _model is not None


def hint_for(player_names: list[str]) -> str:
    """Whisper spells words it has just "read" correctly, so show it the names
    of the players in this game and some football words."""
    return f"A footballer talks about a pickup game. Players: {', '.join(player_names)}. {WHISPER_WORDS}."


async def transcribe(path: Path, player_names: list[str]) -> str:
    """Turn an audio file into text, without blocking the server."""
    started = time.perf_counter()
    if is_cloud():
        text = await _transcribe_groq(path, player_names)
    else:
        text = await asyncio.to_thread(_transcribe_local, path, player_names)
    log.info("Whisper (%s) transcribed in %.1f s", settings.ai_mode, time.perf_counter() - started)
    return text


# --- cloud: Whisper at Groq -------------------------------------------------

def audio_format(data: bytes) -> tuple[str, str]:
    """(file name, content type) from the first bytes of the audio. Groq
    decides how to read a file from its name, and ours has none."""
    if data[:4] == b"OggS":
        return "voice.ogg", "audio/ogg"  # Telegram voice notes
    if data[:4] == b"\x1aE\xdf\xa3":
        return "voice.webm", "audio/webm"  # Android Chrome recordings
    if data[4:8] == b"ftyp":
        return "voice.m4a", "audio/mp4"  # iPhone recordings
    if data[:4] == b"RIFF":
        return "voice.wav", "audio/wav"
    if data[:3] == b"ID3" or data[:2] in (b"\xff\xfb", b"\xff\xf3"):
        return "voice.mp3", "audio/mpeg"
    return "voice.ogg", "audio/ogg"


async def _transcribe_groq(path: Path, player_names: list[str]) -> str:
    if not settings.groq_api_key:
        raise RuntimeError("AI_MODE is cloud but GROQ_API_KEY is not set.")
    data = path.read_bytes()
    name, content_type = audio_format(data)
    form = {
        "model": settings.groq_whisper_model,
        "language": "en",  # Nigerian English and Pidgin both work best as "en"
        "prompt": hint_for(player_names)[:800],
        "response_format": "json",
        "temperature": "0",
    }
    headers = {"Authorization": f"Bearer {settings.groq_api_key}"}

    for wait in (5, 20, None):
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(GROQ_URL, headers=headers, data=form,
                                         files={"file": (name, data, content_type)})
        if response.status_code == 200:
            return response.json().get("text", "").strip()
        # 429 = over the free limit for the moment; 5xx = Groq's side.
        if response.status_code in (429, 500, 502, 503) and wait is not None:
            log.warning("Groq answered %d; trying again in %d s", response.status_code, wait)
            await asyncio.sleep(wait)
            continue
        raise RuntimeError(f"Groq API error {response.status_code}")
    raise RuntimeError("Groq kept failing.")


# --- local: faster-whisper ---------------------------------------------------

def _load():
    global _model
    if _model is None:
        # Imported here: it is slow to import, and not installed at all on the
        # small cloud server (see requirements-local.txt).
        from faster_whisper import WhisperModel

        started = time.perf_counter()
        # The first time, this downloads the model (a few hundred MB).
        _model = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
        log.info("Whisper '%s' loaded in %.1f s", settings.whisper_model,
                 time.perf_counter() - started)
    return _model


def _decode(path: Path):
    """Read any phone audio (webm, mp4, ogg, wav) as 16 kHz mono samples.

    faster-whisper can do this itself, but its decoder breaks with new PyAV
    versions, so we use PyAV (installed with faster-whisper) directly."""
    import av
    import numpy as np

    # Whisper wants 16,000 samples per second, one channel.
    resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
    chunks = []
    with av.open(str(path)) as container:
        for frame in container.decode(audio=0):
            chunks += [out.to_ndarray() for out in resampler.resample(frame)]
        chunks += [out.to_ndarray() for out in resampler.resample(None)]  # the last bit
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    samples = np.concatenate(chunks, axis=1).reshape(-1)
    # 16-bit whole numbers -> decimals between -1 and 1, as Whisper expects.
    return samples.astype(np.float32) / 32768.0


def _transcribe_local(path: Path, player_names: list[str]) -> str:
    model = _load()
    audio = _decode(path)
    if len(audio) < 16000 // 2:  # under half a second: nothing to hear
        return ""
    segments, _ = model.transcribe(
        audio,
        language="en",  # Nigerian English and Pidgin both work best as "en"
        initial_prompt=hint_for(player_names),
        vad_filter=True,  # skip silence, so noise doesn't become made-up words
        condition_on_previous_text=False,
    )
    # "segments" is lazy: the real work happens while we loop over it.
    return " ".join(segment.text.strip() for segment in segments).strip()
