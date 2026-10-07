"""Voice note -> text, with faster-whisper on the CPU."""

import asyncio
import logging
import time
from pathlib import Path

from .config import settings
from .prompts import WHISPER_WORDS

log = logging.getLogger("starboy.speech")

_model = None  # loaded the first time a voice note arrives


def is_loaded() -> bool:
    return _model is not None


def _load():
    global _model
    if _model is None:
        # Imported here because it is slow to import and not needed for typed reports.
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


def _transcribe(path: Path, player_names: list[str]) -> str:
    model = _load()
    audio = _decode(path)
    if len(audio) < 16000 // 2:  # under half a second: nothing to hear
        return ""
    # Whisper spells words it has just "read" correctly, so show it the names
    # of the players in this game and some football words.
    hint = f"A footballer talks about a pickup game. Players: {', '.join(player_names)}. {WHISPER_WORDS}."
    started = time.perf_counter()
    segments, _ = model.transcribe(
        audio,
        language="en",  # Nigerian English and Pidgin both work best as "en"
        initial_prompt=hint,
        vad_filter=True,  # skip silence, so noise doesn't become made-up words
        condition_on_previous_text=False,
    )
    # "segments" is lazy: the real work happens while we loop over it.
    text = " ".join(segment.text.strip() for segment in segments).strip()
    log.info("Whisper transcribed in %.1f s", time.perf_counter() - started)
    return text


async def transcribe(path: Path, player_names: list[str]) -> str:
    """Transcribe an audio file without blocking the server (runs in a thread)."""
    return await asyncio.to_thread(_transcribe, path, player_names)
